from starlette.middleware import Middleware
from starlette.routing import Mount, Route, WebSocketRoute
from starlette.staticfiles import StaticFiles

from starlette_web.common.conf import settings
from starlette_web.contrib.apispec.views import OpenApiView
from starlette_web.contrib.auth.routes import routes as auth_routes
from starlette_web.contrib.admin import admin, AdminMount
from starlette_web.tests.views import (
    HealthCheckAPIView,
    BaseWebsocketTestEndpoint,
    EndpointWithStatusCodeMiddleware,
    EndpointWithCacheMiddleware,
    CancellationWebsocketTestEndpoint,
    AuthenticationWebsocketTestEndpoint,
    FinitePeriodicTaskWebsocketTestEndpoint,
    InfinitePeriodicTaskWebsocketTestEndpoint,
    ChatWebsocketTestEndpoint,
    EmptyResponseAPIView,
    EndpointWithContextSchema,
    EndpointWithTypedMethodSchema,
)
from starlette_web.tests.views.middlewares import (
    SetResponseStatusCode201TestMiddleware,
    CacheMiddleware,
)


# TODO: split auth and api
routes = [
    Mount("/api", routes=auth_routes),
    Route("/openapi", OpenApiView, include_in_schema=False),
    AdminMount("/admin", app=admin.get_app(), name="admin"),
    Mount("/static", app=StaticFiles(directory=settings.STATIC["ROOT_DIR"]), name="static"),
    Mount("/media", app=StaticFiles(directory=settings.MEDIA["ROOT_DIR"]), name="media"),
    Route("/health_check/", HealthCheckAPIView),
    Route("/empty/", EmptyResponseAPIView, include_in_schema=False),
    Route("/context-schema/", EndpointWithContextSchema, include_in_schema=False),
    Route("/typed-schema/", EndpointWithTypedMethodSchema, include_in_schema=True),
    Route(
        "/reset-status-code/",
        EndpointWithStatusCodeMiddleware,
        include_in_schema=False,
        middleware=[Middleware(SetResponseStatusCode201TestMiddleware)],
    ),
    Route(
        "/cachable-response/",
        EndpointWithCacheMiddleware,
        include_in_schema=False,
        middleware=[Middleware(CacheMiddleware)],
    ),
    WebSocketRoute("/ws/test_websocket_base", BaseWebsocketTestEndpoint),
    WebSocketRoute("/ws/test_websocket_cancel", CancellationWebsocketTestEndpoint),
    WebSocketRoute("/ws/test_websocket_auth", AuthenticationWebsocketTestEndpoint),
    WebSocketRoute("/ws/test_websocket_finite_periodic", FinitePeriodicTaskWebsocketTestEndpoint),
    WebSocketRoute(
        "/ws/test_websocket_infinite_periodic", InfinitePeriodicTaskWebsocketTestEndpoint
    ),
    WebSocketRoute("/ws/test_websocket_chat", ChatWebsocketTestEndpoint),

    # Endpoints for APIspec tests with path params
    Route("/{alias:str}/", EmptyResponseAPIView),
    Mount("/{alias1:str}/", routes=[
        Route("/{alias2:str}/", EmptyResponseAPIView),
    ]),
]
