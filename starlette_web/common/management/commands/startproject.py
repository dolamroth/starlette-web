import os
import shutil
from pathlib import Path

import starlette_web
from starlette_web.common.management.alembic_mixin import AlembicMixin
from starlette_web.common.management.base import BaseCommand, CommandError, CommandParser
from starlette_web.common.utils import get_random_string


class Command(BaseCommand, AlembicMixin):
    help = "Initialize directory with project files"
    _alembic_directory_name = "alembic"

    def add_arguments(self, parser: CommandParser):
        parser.add_argument("project_name", type=str)
        parser.add_argument("--advanced_project_template", type=str, default="false")

    async def handle(self, **options):
        current_dir = os.getcwd()
        project_name = options["project_name"]
        is_advanced_project_template = True if options.get("advanced_project_template") == "true" else False

        cwd = Path(current_dir)
        project_dir = cwd / project_name
        files_templates_dir = Path(starlette_web.__path__[0], "common", "conf", "file_templates")
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
        env_template_content = self._read_template_file(
            file_name=Path(files_templates_dir, "env_template.py-tpl"),
        )
        with open(project_dir / ".env", "wt+", encoding="utf-8") as file:
            content = env_template_content.format(
                secret_key=get_random_string(50),
            )
            file.writelines(content.strip() + "\n")

        with open(project_dir / ".env.template", "wt+", encoding="utf-8") as file:
            content = env_template_content.format(
                secret_key="",
            )
            file.writelines(content.strip() + "\n")

        # Setup alembic
        os.chdir(project_dir)
        await self.run_alembic_main(["init", "-t", "async", self._alembic_directory_name])
        if is_advanced_project_template:
            await self._setup_advanced_alembic_conf(
                project_dir=project_dir,
                alembic_env_template=Path(files_templates_dir, "alembic_env_template.py-tpl"),
            )
        else:
            await self._setup_default_alembic_conf(project_dir=project_dir)

    def _read_template_file(self, file_name: Path) -> str:
        if not (file_name.exists() and file_name.is_file()):
            raise CommandError(details=f"Invalid file template path: {str(file_name)}")

        with file_name.open() as file:
            return file.read()

    async def _setup_default_alembic_conf(self, project_dir: Path) -> None:
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

    async def _setup_advanced_alembic_conf(self, project_dir: Path, alembic_env_template: Path) -> None:
        alembic_env_template_content = self._read_template_file(file_name=alembic_env_template)
        with open(project_dir / self._alembic_directory_name / "env.py", "wt") as file:
            file.write(alembic_env_template_content)

        with open(project_dir / "alembic.ini", "rt") as file:
            lines = []
            for line in file:
                if "# file_template = " in line:
                    lines.append(line[2:])
                elif "# revision_environment = false" in line:
                    lines += "revision_environment = true"
                else:
                    lines.append(line)

        with open(project_dir / "alembic.ini", "wt") as file:
            file.writelines(lines)
