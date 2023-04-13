from apispec import APISpec
from starlette.requests import Request

from starlette_web.common.conf import settings
from starlette_web.common.http.base_endpoint import BaseHTTPEndpoint
from starlette_web.common.http.exceptions import NotImplementedByServerError
from starlette_web.common.http.renderers import JSONRenderer
from starlette_web.common.http.responses import TemplateResponse
from starlette_web.common.utils import urljoin
from starlette_web.contrib.apispec.introspection import APISpecSchemaGenerator
from starlette_web.contrib.apispec.marshmallow import StarletteWebMarshmallowPlugin


api_spec = APISpec(
    **settings.APISPEC["CONFIG"],
    plugins=[StarletteWebMarshmallowPlugin()],
)


schemas = APISpecSchemaGenerator(api_spec)


# TODO: think about managing permissions
# TODO: cache view
class OpenApiView(BaseHTTPEndpoint):
    auth_backend = None
    permission_classes = []

    async def get(self, request: Request):
        _format = request.query_params.get("format", "openapi")
        _schema_url = request.url.replace_query_params(format="openapi")

        if _format not in ["openapi", "redoc"]:
            raise NotImplementedByServerError(
                details=(
                    "Server only supports 'redoc' and 'openapi' "
                    "format for OpenAPI documentation."
                )
            )

        if _format == "openapi":
            routes = request.app.routes
            return JSONRenderer(schemas.get_schema(routes))

        return TemplateResponse(
            "apispec/redoc.html",
            context={
                "REDOC_SPEC_URL": str(_schema_url),
                "REDOC_JS_URL": urljoin(settings.STATIC["URL"], "apispec", "redoc.js"),
                "REDOC_TITLE": "OPENAPI documentation",
                "request": request,
            },
        )
