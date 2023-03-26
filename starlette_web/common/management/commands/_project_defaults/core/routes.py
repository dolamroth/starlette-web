# flake8: noqa

from starlette.routing import Mount, Route, WebSocketRoute
from starlette.staticfiles import StaticFiles

from starlette_web.common.conf import settings
from starlette_web.contrib.apispec.routes import routes as apispec_routes
from starlette_web.contrib.admin import admin, AdminMount


routes = [
    Mount(
        settings.STATIC["URL"],
        app=StaticFiles(directory=settings.STATIC["ROOT_DIR"]),
        name="static",
    ),

    # Admin-panel is not yet integral part of the framework,
    # so it requires a bit of hacking with custom mount class,
    # to manage static files right
    AdminMount("/admin", app=admin.get_app(), name="admin"),

    Mount("/openapi", routes=apispec_routes),
]
