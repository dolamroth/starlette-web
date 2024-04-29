import os
import sys

from starlette_web.common.conf.utils import parse_startapp_known_args


def main():
    current_settings = os.environ.get("STARLETTE_SETTINGS_MODULE")

    try:
        # At this point, user-defined settings may not exist
        # (i.e., if user calls startproject command),
        # so pass global_settings instead
        settings_module = "starlette_web.common.conf.global_settings"

        args = parse_startapp_known_args()
        if args.settings:
            settings_module = args.settings

        os.environ.setdefault("STARLETTE_SETTINGS_MODULE", settings_module)

        if len(sys.argv) < 2:
            raise Exception(
                "Missing command name. Correct syntax is: " '"starlette-web-admin command_name ..."'
            )

        from starlette_web.common.app import get_asgi_application
        from starlette_web.common.management.base import fetch_command_by_name

        command = fetch_command_by_name(sys.argv[1])
        app = get_asgi_application(use_pool=args.use_pool)
        command(app).run_from_command_line(sys.argv)
    finally:
        if current_settings:
            os.environ["STARLETTE_SETTINGS_MODULE"] = current_settings
        else:
            os.unsetenv("STARLETTE_SETTINGS_MODULE")


if __name__ == "__main__":
    sys.path.append(os.getcwd())
    main()
