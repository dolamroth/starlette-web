import os
import sys


def main():
    current_settings = os.environ.get("STARLETTE_SETTINGS_MODULE")

    try:
        # At this point, user-defined settings may not exist
        # (i.e., if user calls startproject command),
        # so pass global_settings instead
        settings_module = "starlette_web.common.conf.global_settings"

        sys_argv = list(sys.argv).copy()
        for arg in sys_argv.copy():
            if arg.startswith("--settings="):
                settings_module = arg[11:]
                sys_argv.remove(arg)

        os.environ.setdefault("STARLETTE_SETTINGS_MODULE", settings_module)

        if len(sys_argv) < 1:
            raise Exception(
                'Missing command name. Correct syntax is: '
                '"starlette-web-admin command_name ..."'
            )

        from starlette_web.common.conf import settings
        from starlette_web.common.app import get_app
        from starlette_web.common.management.base import fetch_command_by_name
        command = fetch_command_by_name(sys_argv[1])
        app = get_app(use_pool=settings.DB_USE_CONNECTION_POOL_FOR_MANAGEMENT_COMMANDS)
        command(app).run_from_command_line(sys_argv)
    finally:
        if current_settings:
            os.environ["STARLETTE_SETTINGS_MODULE"] = current_settings
        else:
            os.unsetenv("STARLETTE_SETTINGS_MODULE")


if __name__ == "__main__":
    sys.path.append(os.getcwd())
    main()
