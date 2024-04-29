# flake8: noqa

import os

from starlette_web.common.conf.utils import parse_startapp_known_args
args = parse_startapp_known_args()

os.environ.setdefault("STARLETTE_SETTINGS_MODULE", args.settings or "starlette_web.tests.settings")

from starlette_web.common.app import get_asgi_application
app = get_asgi_application(run_checks_on_startup=not args.skip_checks)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=args.host, port=args.port)
