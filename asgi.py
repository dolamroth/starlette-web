import os
import sys
import uvicorn

from starlette_web.common.app import get_app


if __name__ == "__main__":
    settings_module = "starlette_web.tests.settings"
    for arg in sys.argv:
        if arg.startswith("--settings="):
            settings_module = arg[11:]

    os.environ.setdefault("STARLETTE_SETTINGS_MODULE", settings_module)

    app = get_app()
    uvicorn.run(app, host="127.0.0.1", port=80)
