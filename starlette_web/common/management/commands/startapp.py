import os
import shutil
from pathlib import Path

from starlette_web.common.conf.app_manager import app_manager
from starlette_web.common.management.base import BaseCommand, CommandError, CommandParser


class Command(BaseCommand):
    help = "Initialize application directory"

    def add_arguments(self, parser: CommandParser):
        parser.add_argument("app_name", type=str)

    async def handle(self, **options):
        current_dir = os.getcwd()
        app_name = options["app_name"]

        cwd = Path(current_dir)
        if not (cwd / "command.py").is_file():
            raise CommandError(details="This command may only be run in project root directory.")

        app_dir = cwd / app_name
        if app_dir.is_file() or app_dir.is_symlink():
            raise CommandError(
                details=(
                    f"Cannot create application directory {app_dir}. "
                    "A file/link with such name exists in the current directory."
                )
            )

        if app_dir.is_dir():
            raise CommandError(details=f"Directory {app_dir} already exists. Exiting.")

        app_manager.register_apps()
        if app_name in app_manager.app_names:
            existing_app = app_manager.app_names[app_name]
            raise CommandError(
                details=f"Application with name {app_name} already installed in "
                f"settings.INSTALLED_APPS ({existing_app})."
            )

        app_dir.mkdir()
        defaults_dir = Path(__file__).parent / "_app_defaults"

        for source_file in defaults_dir.iterdir():
            if source_file.is_file() and source_file.name.endswith(".py"):
                target_file = app_dir / source_file.name
                shutil.copy(source_file, target_file)

        with open(app_dir / "apps.py", "rt") as file:
            lines = []
            for line in file:
                lines.append(line.replace("__APPNAME", app_name))

        with open(app_dir / "apps.py", "wt") as file:
            file.writelines(lines)
