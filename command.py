import argparse
import os
import sys

from starlette_web.common.app import get_asgi_application
from starlette_web.common.management.base import fetch_command_by_name, CommandError


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--settings", default="starlette_web.tests.settings", required=False)
    args, _ = parser.parse_known_args()
    os.environ.setdefault("STARLETTE_SETTINGS_MODULE", args.settings)

    if len(sys.argv) < 2:
        raise CommandError(
            'Missing command name. Correct syntax is: "python command.py command_name ..."'
        )

    from starlette_web.common.conf import settings

    command = fetch_command_by_name(sys.argv[1])
    app = get_asgi_application(use_pool=settings.DB_USE_CONNECTION_POOL_FOR_MANAGEMENT_COMMANDS)
    command(app).run_from_command_line(sys.argv)
