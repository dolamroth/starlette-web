import os
import pkgutil
from argparse import ArgumentParser
from difflib import get_close_matches
from functools import partial
from typing import Optional, List, Type, Dict, Coroutine, Any, Callable

import anyio
from anyio._core._eventloop import T_Retval

from starlette_web.common.app import get_app, WebApp
from starlette_web.common.conf import settings
from starlette_web.common.http.exceptions import BaseApplicationError
from starlette_web.common.utils import import_string


class CommandError(BaseApplicationError):
    message = "Error while running a user-defined command."


class CommandParser(ArgumentParser):
    """
    Customized ArgumentParser class to improve some error messages and prevent
    SystemExit in several occasions, as SystemExit is unacceptable when a
    command is called programmatically.
    """

    def __init__(self, *, missing_args_message=None, called_from_command_line=None, **kwargs):
        self.called_from_command_line = called_from_command_line
        super().__init__(**kwargs)

    def error(self, message):
        if self.called_from_command_line:
            super().error(message)
        else:
            raise CommandError(message)


class BaseCommand:
    help: Optional[str] = None

    def __init__(self, app):
        self.parser: Optional[CommandParser] = None
        self.app: WebApp = app

    def create_parser(self, argv, called_from_command_line=True):
        parser = CommandParser(
            prog="%s %s" % (argv[0], argv[1]),
            description=self.help or None,
            called_from_command_line=called_from_command_line,
        )

        return parser

    def add_arguments(self, parser: CommandParser):
        # Redefine in inherited classes
        pass

    async def handle(self, **options):
        raise NotImplementedError

    async def _handle_wrapper(self, **options):
        async with self.app.router.lifespan_context(self.app) as state:
            await self.handle(_lifespan_state=state, **options)

    def prepare_command_function(
        self,
        argv,
        called_from_command_line,
    ) -> Callable[..., Coroutine[Any, Any, T_Retval]]:
        self.parser = self.create_parser(
            argv,
            called_from_command_line=called_from_command_line,
        )
        self.add_arguments(self.parser)
        namespace = self.parser.parse_args(args=argv[2:])
        kwargs = namespace.__dict__
        return partial(self._handle_wrapper, **kwargs)

    def run_from_command_line(self, argv: List[str]):
        func = self.prepare_command_function(argv, True)
        anyio.run(func)

    async def run_from_code(self, argv: List[str]):
        coroutine = self.prepare_command_function(argv, False)()
        await coroutine


def _get_app_path_by_name(app: str) -> str:
    """
    Lookup possible locations for management commands.
    Firstly, local project directories are checked.
    If respective module was not found,
    trying to seek in virtual environment.
    """
    module_name, _, module_rest = app.partition(".")
    found_local_module = None
    for module_info in pkgutil.iter_modules([module_name]):
        if module_info.ispkg:
            found_local_module = module_info.name

    app_path = app.replace(".", os.sep)

    if not found_local_module:
        try:
            venv_module = __import__(module_name)
            prefix = os.path.dirname(venv_module.__path__[0]).rstrip(os.sep)
        except (OSError, SystemError, ImportError, IndexError):
            prefix = ""

        if prefix:
            app_path = prefix.rstrip(os.sep) + os.sep + app_path.lstrip(os.sep)

    return app_path


def list_commands() -> Dict[str, str]:
    command_files = {}

    installed_apps = settings.INSTALLED_APPS
    if "starlette_web.common" not in installed_apps:
        installed_apps = ["starlette_web.common"] + installed_apps

    for app in installed_apps:
        modules = [os.sep.join([_get_app_path_by_name(app), "management", "commands"])]
        for module_info in pkgutil.iter_modules(modules):
            if module_info.name.startswith("_") or module_info.ispkg:
                continue

            if module_info.name in command_files:
                raise CommandError(
                    details=f"Command '{module_info.name}' is declared in multiple modules."
                )

            command_files[module_info.name] = ".".join(
                [app, "management", "commands", module_info.name, "Command"]
            )

    return command_files


def fetch_command_by_name(command_name: str) -> Type[BaseCommand]:
    commands = list_commands()

    if command_name in commands:
        try:
            command = import_string(commands[command_name])

            # isinstance not working for class, imported with import_module
            is_instance = any([kls for kls in command.__mro__ if kls == BaseCommand])
            if not is_instance:
                raise CommandError(
                    "Command must be inherited from common.management.base.BaseCommand"
                )

            return command
        except (ImportError, AssertionError) as exc:
            raise CommandError from exc

    error_message = f"Command '{command_name}' not found."
    possible_matches = get_close_matches(command_name, list(commands.keys()))
    if possible_matches:
        details = f"Did you mean \"{possible_matches[0]}\"?"
    else:
        details = ""
    raise CommandError(message=error_message, details=details)


async def call_command(command_name, command_args: List[str]):
    command = fetch_command_by_name(command_name)
    app = get_app(
        use_pool=settings.DB_USE_CONNECTION_POOL_FOR_MANAGEMENT_COMMANDS,
        run_checks_on_startup=False,
    )
    await command(app).run_from_code(["command.py", command_name] + command_args)
