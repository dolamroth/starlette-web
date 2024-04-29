import os
import sys

from starlette_web.common.app import get_asgi_application
from starlette_web.common.conf.utils import parse_startapp_known_args
from starlette_web.common.management.base import fetch_command_by_name, CommandError


if __name__ == "__main__":
    args = parse_startapp_known_args()
    os.environ.setdefault("STARLETTE_SETTINGS_MODULE", args.settings or "core.settings")

    if len(sys.argv) < 2:
        raise CommandError(
            'Missing command name. Correct syntax is: "python command.py command_name ..."'
        )

    command = fetch_command_by_name(sys.argv[1])
    app = get_asgi_application(
        use_pool=args.use_pool,
        run_checks_on_startup=not args.skip_checks,
    )
    command(app).run_from_command_line(sys.argv)
