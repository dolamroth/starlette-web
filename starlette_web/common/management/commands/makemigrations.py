import datetime

from starlette_web.common.management.alembic_mixin import AlembicMixin
from starlette_web.common.management.base import BaseCommand, CommandParser


class Command(BaseCommand, AlembicMixin):
    help = "Make new migrations files (helper for alembic revision)"

    def add_arguments(self, parser: CommandParser):
        parser.add_argument(
            "-n",
            "--name",
            type=str,
            required=False,
            help="New migration name",
        )

        parser.add_argument(
            "--empty",
            const=True,
            action="store_const",
            default=False,
            required=False,
            help="Whether to create an empty migration",
        )

    async def handle(self, **options):
        revision_name = "auto_" + datetime.datetime.now().strftime("%Y%m%d_%H%M")
        if options.get("name"):
            revision_name = options["name"]

        if options.get("empty", False):
            await self.run_alembic_main(["revision", "-m", revision_name])
            print("New empty migration generated.")

        else:
            stdout, stderr = await self.run_alembic_main(["check"])

            if "Target database is not up to date" in stdout:
                print(stdout.strip())

            else:
                stdout, stderr = await self.run_alembic_main([
                    "revision",
                    "-m",
                    revision_name,
                    "--autogenerate",
                ])

                print(stdout.strip())
