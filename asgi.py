from starlette_web.common.app import get_asgi_application


app = get_asgi_application()


if __name__ == "__main__":
    import os
    import sys
    import uvicorn

    settings_module = "starlette_web.tests.settings"
    for arg in sys.argv:
        if arg.startswith("--settings="):
            settings_module = arg[11:]

    os.environ.setdefault("STARLETTE_SETTINGS_MODULE", settings_module)
    uvicorn.run(app, host="127.0.0.1", port=80)
