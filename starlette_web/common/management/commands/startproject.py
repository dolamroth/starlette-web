import os
import shutil
from pathlib import Path

from starlette_web.common.management.alembic_mixin import AlembicMixin
from starlette_web.common.management.base import BaseCommand, CommandError, CommandParser
from starlette_web.common.utils import get_random_string
from jinja2 import Template


class Command(BaseCommand, AlembicMixin):
    help = "Initialize directory with project files"
    _alembic_directory_name = "alembic"

    def add_arguments(self, parser: CommandParser):
        parser.add_argument("project_name", type=str)
        parser.add_argument("--migration_prefix", type=str, default="auto")

    async def handle(self, **options):
        project_name = options["project_name"]
        migration_prefix = options.get("migration_prefix")

        project_dir = Path(os.getcwd()) / project_name
        if project_dir.is_file() or project_dir.is_symlink():
            raise CommandError(
                details=(
                    f"Cannot create project directory {project_name}. "
                    "A file/link with such name exists in the current directory."
                )
            )

        if project_dir.is_dir():
            raise CommandError(details=f"Directory {project_dir} already exists. Exiting.")

        project_dir.mkdir()
        defaults_dir = Path(__file__).parent / "_project_defaults"

        shutil.copytree(
            defaults_dir / "core",
            project_dir / "core",
        )
        for filename in ["command.py", "asgi.py", "__init__.py"]:
            shutil.copy(
                defaults_dir / filename,
                project_dir / filename,
            )

        # Setup base directories
        (project_dir / "static").mkdir()
        (project_dir / "templates").mkdir()

        # Setup env files
        env_template_content = self._read_template_file(file_name=defaults_dir / ".env_template")
        with open(project_dir / ".env", "wt+", encoding="utf-8") as file:
            file.write(env_template_content.format(secret_key=get_random_string(50)))

        with open(project_dir / ".env.template", "wt+", encoding="utf-8") as file:
            file.write(env_template_content.format(secret_key=""))

        # Setup alembic
        os.chdir(project_dir)
        await self.run_alembic_main(["init", "-t", "async", self._alembic_directory_name])
        await self._setup_alembic_conf(
            project_dir=project_dir,
            env_file_path=defaults_dir / "alembic" / "env.py-tpl",
            migration_prefix=migration_prefix,
        )

    @staticmethod
    def _read_template_file(file_name: Path) -> str:
        if not (file_name.exists() and file_name.is_file()):
            raise CommandError(details=f"Invalid file template path: {str(file_name)}")

        with file_name.open() as file:
            return file.read()

    async def _setup_alembic_conf(self, project_dir: Path, env_file_path: Path, migration_prefix: str) -> None:
        alembic_env_content = Template(self._read_template_file(file_name=env_file_path))
        with open(project_dir / self._alembic_directory_name / "env.py", "wt") as file:
            file.write(alembic_env_content.render(migration_prefix=migration_prefix))

        with open(project_dir / "alembic.ini", "rt") as file:
            lines = []
            for line in file:
                if "# file_template = " in line:
                    lines.append(line[2:])
                elif migration_prefix == "auto" and "# revision_environment = false" in line:
                    lines += "revision_environment = true"
                else:
                    lines.append(line)

        with open(project_dir / "alembic.ini", "wt") as file:
            file.writelines(lines)
