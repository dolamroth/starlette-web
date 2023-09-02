import os
import shutil
from pathlib import Path

from starlette_web.common.management.alembic_mixin import AlembicMixin
from starlette_web.common.management.base import BaseCommand, CommandError, CommandParser
from starlette_web.common.utils import get_random_string


class Command(BaseCommand, AlembicMixin):
    help = "Initialize directory with project files"
    _alembic_directory_name = "alembic"

    def add_arguments(self, parser: CommandParser):
        parser.add_argument("project_name", type=str)

    async def handle(self, **options):
        current_dir = os.getcwd()
        project_name = options["project_name"]

        cwd = Path(current_dir)
        project_dir = cwd / project_name
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

        env_template = """
APP_DEBUG=false
SITE_URL="https://web.project.com/"
SECRET_KEY={secret_key}

DB_HOST=localhost
DB_PORT=5432
DB_NAME=web_project
DB_USERNAME=postgres
DB_PASSWORD=postgres
DB_ECHO=false
        """

        with open(project_dir / ".env", "wt+", encoding="utf-8") as file:
            content = env_template.format(
                secret_key=get_random_string(50),
            )
            file.writelines(content.strip() + "\n")

        with open(project_dir / ".env.template", "wt+", encoding="utf-8") as file:
            content = env_template.format(
                secret_key="",
            )
            file.writelines(content.strip() + "\n")

        # Setup base directories

        (project_dir / "static").mkdir()
        (project_dir / "templates").mkdir()

        # Setup alembic
        os.chdir(project_dir)
        await self.run_alembic_main(["init", "-t", "async", self._alembic_directory_name])
        with open(project_dir / self._alembic_directory_name / "env.py", "rt") as file:
            lines = []
            for line in file:
                if line.strip() == "target_metadata = None":
                    lines += [
                        "from starlette_web.common.conf import settings\n",
                        "from starlette_web.common.conf.app_manager import app_manager\n",
                        "from starlette_web.common.database.model_base import ModelBase\n",
                        "app_manager.import_models()\n" "target_metadata = ModelBase.metadata\n",
                    ]
                else:
                    lines.append(line)

        with open(project_dir / self._alembic_directory_name / "env.py", "wt") as file:
            file.writelines(lines)

        with open(project_dir / "alembic.ini", "rt") as file:
            lines = []
            for line in file:
                if "# file_template = " in line:
                    lines.append(line[2:])
                else:
                    lines.append(line)

        with open(project_dir / "alembic.ini", "wt") as file:
            file.writelines(lines)
