import logging

from starlette import status
from marshmallow import Schema, fields

from starlette_web.contrib.auth.models import User
from starlette_web.common.http.base_endpoint import BaseHTTPEndpoint


logger = logging.getLogger(__name__)


class ServicesCheckSchema(Schema):
    postgres = fields.Str()


class HealthCheckSchema(Schema):
    services = fields.Nested(ServicesCheckSchema)
    errors = fields.List(fields.Str)


class HealthCheckAPIView(BaseHTTPEndpoint):
    """Allows controlling status of web application (live ASGI and pg connection)"""

    auth_backend = None
    response_schema = HealthCheckSchema

    async def get(self, *_):
        """
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
            await User.async_filter(self.db_session)
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
