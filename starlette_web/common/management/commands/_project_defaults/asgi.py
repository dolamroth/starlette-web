# flake8: noqa

import argparse
import os


os.environ.setdefault("STARLETTE_SETTINGS_MODULE", "core.settings")
from starlette_web.common.app import get_asgi_application

app = get_asgi_application()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--settings", required=False)
    args, _ = parser.parse_known_args()
    if args.settings:
        os.environ.setdefault("STARLETTE_SETTINGS_MODULE", args.settings)

    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=80)
