from starlette_web.common.management.alembic_mixin import AlembicMixin
from starlette_web.common.management.base import BaseCommand, CommandParser


class Command(BaseCommand, AlembicMixin):
    help = "Migrate to selected alembic revision"

    def add_arguments(self, parser: CommandParser):
        parser.add_argument(
            "name",
            type=str,
            help="Alembic revision slug to migrate to",
            nargs="?",
        )

    async def handle(self, **options):
        revision_name = options.get("name")

        if revision_name is None:
            stdout, stderr = await self.run_alembic_main(["upgrade", "head"])

        elif revision_name.startswith("+") and revision_name[1:].isdigit():
            stdout, stderr = await self.run_alembic_main(["upgrade", revision_name])

        elif revision_name.startswith("-") and revision_name[1:].isdigit():
            stdout, stderr = await self.run_alembic_main(["downgrade", revision_name])

        else:
            stdout, stderr = await self.run_alembic_main(["upgrade", revision_name])
            print(stdout.strip())
            print(stderr.strip())

            stdout, stderr = await self.run_alembic_main(["downgrade", revision_name])

        print(stdout.strip())
        print(stderr.strip())
