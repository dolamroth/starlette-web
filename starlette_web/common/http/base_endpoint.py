import logging
from typing import (
    Type, Union, Iterable, ClassVar, Optional, Mapping, List, Awaitable, Dict,
)

from marshmallow import Schema, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status
from starlette.background import BackgroundTasks
from starlette.exceptions import HTTPException
from starlette.endpoints import HTTPEndpoint
from starlette.requests import Request
from starlette.responses import Response
from webargs_starlette import WebargsHTTPException, StarletteParser

from starlette_web.common.app import WebApp
from starlette_web.common.authorization.backends import (
    BaseAuthenticationBackend,
    NoAuthenticationBackend,
)
from starlette_web.common.authorization.permissions import PermissionType
from starlette_web.common.authorization.base_user import AnonymousUser
from starlette_web.common.database.model_base import ModelBase
from starlette_web.common.conf import settings
from starlette_web.common.http.exceptions import (
    UnexpectedError,
    BaseApplicationError,
    InvalidParameterError,
    PermissionDeniedError,
)
from starlette_web.common.http.renderers import BaseRenderer
from starlette_web.common.utils import import_string


logger = logging.getLogger(__name__)


class BaseHTTPEndpoint(HTTPEndpoint):
    """
    Base View witch used as a base class for every API's endpoints
    """

    app = None
    request: Request
    db_session: AsyncSession
    request_schema: ClassVar[Type[Schema]]
    response_schema: ClassVar[Type[Schema]]
    auth_backend: ClassVar[Type[BaseAuthenticationBackend]] = NoAuthenticationBackend
    permission_classes: ClassVar[List[PermissionType]] = []
    request_parser: ClassVar[Type[StarletteParser]] = import_string(settings.DEFAULT_REQUEST_PARSER)
    response_renderer: ClassVar[Type[BaseRenderer]] = import_string(
        settings.DEFAULT_RESPONSE_RENDERER
    )

    async def dispatch(self) -> None:
        """
        This method is called in every request.
        So, we can use this one for custom authentication and exception handling
        """

        self.request = Request(self.scope, receive=self.receive)
        self.app: WebApp = self.scope.get("app")

        handler_name = "get" if self.request.method == "HEAD" else self.request.method.lower()
        handler: Awaitable[Response] = getattr(self, handler_name, self.method_not_allowed)

        try:
            async with self.app.session_maker() as session:
                try:
                    self.request.state.db_session = session
                    self.db_session = session
                    await self._authenticate()
                    await self._check_permissions()

                    response: Response = await handler(self.request)  # noqa
                    await session.commit()

                except Exception as err:
                    await session.rollback()
                    raise err

        except (BaseApplicationError, WebargsHTTPException, HTTPException) as err:
            raise err

        except Exception as err:
            msg_template = "Unexpected error handled: %r"
            logger.exception(msg_template, err)
            raise UnexpectedError(msg_template % (err,))

        # Circumvent strange design decision of uvicorn, which raises on non-empty response
        # (even with b"null") when status code is 204 or 304
        if response.status_code in settings.STATUS_CODES_WITH_NO_BODY:
            if settings.REMOVE_BODY_FROM_RESPONSE_WITH_NO_BODY:
                response.body = b""
            elif response.body:
                response.headers.update({"content-length": str(len(response.body))})

        await response(self.scope, self.receive, self.send)

    async def _authenticate(self):
        if self.auth_backend:
            backend = self.auth_backend(self.request, self.scope)
            user = await backend.authenticate()
            self.scope["user"] = user
        else:
            self.scope["user"] = AnonymousUser()

    async def _check_permissions(self):
        for permission_class in self.permission_classes:
            try:
                has_permission = await permission_class().has_permission(self.request, self.scope)
                if not has_permission:
                    raise PermissionDeniedError
            # Exception may be raised inside permission_class, to pass additional details
            except PermissionDeniedError as exc:
                raise exc
            except Exception as exc:
                raise PermissionDeniedError from exc

    async def _validate(
        self,
        request,
        schema: Type[Schema] = None,
        partial_: bool = False,
        location: str = None,
        context: Optional[Dict] = None,
    ) -> Optional[Mapping]:
        """Simple validation, based on marshmallow's schemas"""

        schema_class = schema or self.request_schema
        schema_kwargs = {}
        if partial_:
            schema_kwargs["partial"] = [field for field in schema_class().fields]
        if context:
            schema_kwargs["context"] = context

        schema_obj, cleaned_data = schema_class(**schema_kwargs), {}
        try:
            cleaned_data = await self.request_parser().parse(schema_obj, request, location=location)
            if hasattr(schema_obj, "is_valid") and callable(schema_obj.is_valid):
                schema_obj.is_valid(cleaned_data)

        except ValidationError as e:
            # TODO: check that details is str / flatten
            raise InvalidParameterError(details=e.data)
        except WebargsHTTPException as e:
            # TODO: check that details is str / flatten
            # Make return code for invalidated request schema consistent within project
            e.status_code = InvalidParameterError.status_code
            raise e

        return cleaned_data

    def _response(
        self,
        data: Union[ModelBase, Iterable[ModelBase], dict] = None,
        status_code: int = status.HTTP_200_OK,
        headers: Mapping[str, str] = None,
        background: Optional[BackgroundTasks] = None,
        context: Optional[Dict] = None,
    ) -> BaseRenderer:
        """
        A shorthand for response_renderer plus serializing data and passing text status.
        To be used primarily with JSONRenderer and such.
        """
        if (data is not None) and self.response_schema:
            schema_kwargs = {}
            if isinstance(data, Iterable) and not isinstance(data, dict):
                schema_kwargs["many"] = True
            if context is not None:
                schema_kwargs["context"] = context

            payload = self.response_schema(**schema_kwargs).dump(data)
        else:
            payload = data

        return self.response_renderer(
            payload,
            status_code=status_code,
            headers=headers,
            background=background,
        )
