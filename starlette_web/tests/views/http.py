import logging

import anyio
from sqlalchemy import select
from starlette import status

from starlette_web.contrib.auth.models import User
from starlette_web.common.http.base_endpoint import BaseHTTPEndpoint
from starlette_web.common.authorization.permissions import AllowAnyPermission
from starlette_web.tests.views.schemas import (
    HealthCheckSchema,
    TypedMethodFieldRequestSchema,
    TypedMethodFieldResponseSchema,
    EndpointWithContextRequestSchema,
    EndpointWithContextResponseSchema,
)


logger = logging.getLogger(__name__)


class HealthCheckAPIView(BaseHTTPEndpoint):
    """Allows controlling status of web application (live ASGI and pg connection)"""

    auth_backend = None
    response_schema = HealthCheckSchema

    async def get(self, *_):
        """
        summary: Health check
        description: Health check of services
        responses:
          200:
            description: Services with status
            content:
              application/json:
                schema: HealthCheckSchema
          503:
            description: Service unavailable
        tags: ["Health check"]
        """
        response_data = {"services": {}, "errors": []}
        result_status = status.HTTP_200_OK

        try:
            query = select(User)
            _ = (await self.request.state.db_session.execute(query)).scalars().first()

            # This is for test
            await AllowAnyPermission().has_permission(self.request, self.scope)
        except Exception as error:
            error_msg = f"Couldn't connect to DB: {error.__class__.__name__} '{error}'"
            logger.exception(error_msg)
            response_data["services"]["postgres"] = "down"
            response_data["errors"].append(error_msg)
        else:
            response_data["services"]["postgres"] = "ok"

        services = response_data.get("services").values()

        if "down" in services or response_data.get("errors"):
            response_data["status"] = "down"
            result_status = status.HTTP_503_SERVICE_UNAVAILABLE

        return self._response(
            data=response_data,
            status_code=result_status,
        )


class EmptyResponseAPIView(BaseHTTPEndpoint):
    auth_backend = None

    async def get(self, *_):
        """
        summary: Empty response
        description: Empty response (204) for test
        responses:
          204:
            description: Empty response for test
        tags: ["Test"]
        """
        return self._response(status_code=204)


class EndpointWithContextSchema(BaseHTTPEndpoint):
    auth_backend = None
    request_schema = EndpointWithContextRequestSchema
    response_schema = EndpointWithContextResponseSchema

    async def post(self, request):
        data = await self._validate(request, context={"add": 1})
        return self._response(
            {"value": data.get("value", 0)},
            context={"add": 1},
        )


class EndpointWithTypedMethodSchema(BaseHTTPEndpoint):
    auth_backend = None
    request_schema = TypedMethodFieldRequestSchema
    response_schema = TypedMethodFieldResponseSchema

    async def post(self, request):
        """
        summary: TypedMethodField
        description: Endpoint with typed method field
        requestBody:
          required: true
          description: Method field
          content:
            application/json:
              schema: TypedMethodFieldRequestSchema
        responses:
          200:
            description: Test Response
            content:
              application/json:
                schema: TypedMethodFieldResponseSchema
        tags: ["Test"]
        """
        data = await self._validate(request)
        return self._response(data)


class EndpointWithStatusCodeMiddleware(BaseHTTPEndpoint):
    auth_backend = None

    async def get(self, *_):
        # Middleware should reset status code to 201
        return self._response(status_code=200)


class EndpointWithCacheMiddleware(BaseHTTPEndpoint):
    auth_backend = None

    async def get(self, *_):
        await anyio.sleep(2.0)
        return self._response(status_code=200)
