import logging
import logging.config
from typing import Any, Optional

import httpx
from starlette.requests import Request
from starlette.responses import BackgroundTask
from webargs_starlette import WebargsHTTPException

from starlette_web.common.conf import settings
from starlette_web.common.http.exceptions import BaseApplicationError
from starlette_web.common.http.renderers import BaseRenderer, JSONRenderer
from starlette_web.common.http.schemas import get_error_schema_class


class BaseExceptionHandler:
    renderer_class: BaseRenderer = JSONRenderer

    def _log_message(self, exc: Exception, error_data: dict, level=logging.ERROR):
        logger = logging.getLogger(__name__)

        error_details = {
            "error": error_data.get("error", "Unbound exception"),
            "details": error_data.get("details", str(exc)),
        }
        message = "{exc.__class__.__name__} '{error}': [{details}]".format(exc=exc, **error_details)
        logger.log(level, message, exc_info=(level == logging.ERROR))

    def _get_error_message(self, request: Request, exc: Exception) -> str:
        return "Something went wrong!"

    def _get_error_details(self, request: Request, exc: Exception) -> str:
        return f"Raised Error: {exc.__class__.__name__}"

    def _get_status_code(self, request: Request, exc: Exception) -> int:
        return getattr(exc, "status_code", httpx.codes.INTERNAL_SERVER_ERROR.value)

    def _get_response_data(self, request: Request, exc: Exception) -> Any:
        _status_code = self._get_status_code(request, exc)

        payload = {
            "error": self._get_error_message(request, exc),
        }
        if settings.APP_DEBUG or _status_code == httpx.codes.BAD_REQUEST.value:
            payload["details"] = self._get_error_details(request, exc)

        error_schema = get_error_schema_class()()
        return error_schema.dump(payload)

    def _on_error_action(self, request: Request, exc: Exception):
        status_code = self._get_status_code(request, exc)
        error_message = self._get_error_message(request, exc)
        payload = {"error": error_message}

        log_level = logging.ERROR if httpx.codes.is_error(status_code) else logging.WARNING
        self._log_message(exc, payload, log_level)

    def _get_headers(self, request: Request, exc: Exception) -> Optional[dict]:
        return None

    def _get_background_tasks(self, request: Request, exc: Exception) -> Optional[BackgroundTask]:
        return None

    def __call__(self, request: Request, exc: Exception) -> BaseRenderer:
        self._on_error_action(request, exc)

        return self.renderer_class(
            content=self._get_response_data(request, exc),
            status_code=self._get_status_code(request, exc),
            background=self._get_background_tasks(request, exc),
            headers=self._get_headers(request, exc),
        )


class BaseApplicationErrorHandler(BaseExceptionHandler):
    def _get_error_details(self, request: Request, exc: BaseApplicationError) -> str:
        return exc.details

    def _get_error_message(self, request: Request, exc: BaseApplicationError) -> str:
        return exc.message


class WebargsHTTPExceptionHandler(BaseExceptionHandler):
    def _get_error_details(self, request: Request, exc: WebargsHTTPException):
        return exc.messages.get("json") or exc.messages.get("form") or exc.messages

    def _get_error_message(self, request: Request, exc: WebargsHTTPException) -> str:
        return httpx.codes.BAD_REQUEST.name

    def _get_status_code(self, request: Request, exc: Exception) -> int:
        return httpx.codes.BAD_REQUEST.value
