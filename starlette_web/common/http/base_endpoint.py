from typing import Type, Union, Iterable, Any, ClassVar, Optional, Mapping

from marshmallow import Schema, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status
from starlette.background import BackgroundTasks
from starlette.exceptions import HTTPException
from starlette.endpoints import HTTPEndpoint
from webargs_starlette import parser, WebargsHTTPException

from starlette_web.auth.backend import LoginRequiredAuthBackend
from starlette_web.common.http.exceptions import (
    NotFoundError,
    UnexpectedError,
    BaseApplicationError,
    InvalidParameterError,
)
from starlette_web.common.http.renderers import BaseRenderer, JSONRenderer
from starlette_web.common.http.requests import PRequest
from starlette_web.common.http.statuses import ResponseStatus
from starlette_web.common.models import DBModel
from starlette_web.common.utils import get_logger


logger = get_logger(__name__)


class BaseHTTPEndpoint(HTTPEndpoint):
    """
    Base View witch used as a base class for every API's endpoints
    """

    app = None
    request: PRequest
    db_model: ClassVar[DBModel]
    db_session: AsyncSession
    schema_request: ClassVar[Type[Schema]]
    schema_response: ClassVar[Type[Schema]]
    auth_backend = LoginRequiredAuthBackend
    renderer: Type[BaseRenderer] = JSONRenderer

    async def dispatch(self) -> None:
        """
        This method is calling in every request.
        So, we can use this one for customs authenticate and catch all exceptions
        """

        self.request = PRequest(self.scope, receive=self.receive)
        self.app = self.scope.get("app")

        handler_name = "get" if self.request.method == "HEAD" else self.request.method.lower()
        handler = getattr(self, handler_name, self.method_not_allowed)

        try:
            async with self.app.session_maker() as session:
                self.request.db_session = session
                self.db_session = session

                if self.auth_backend:
                    backend = self.auth_backend(self.request)
                    user, session_id = await backend.authenticate()
                    self.scope["user"] = user
                    self.request.user_session_id = session_id

                response = await handler(self.request)  # noqa
                await self.db_session.commit()

        except (BaseApplicationError, WebargsHTTPException, HTTPException) as err:
            await self.db_session.rollback()
            raise err

        except Exception as err:
            await self.db_session.rollback()
            msg_template = "Unexpected error handled: %r"
            logger.exception(msg_template, err)
            raise UnexpectedError(msg_template % (err,))

        await response(self.scope, self.receive, self.send)

    async def _get_object(
        self, instance_id, db_model: Type[DBModel] = None, **filter_kwargs
    ) -> DBModel:
        """
        Returns current object (only for logged-in or admin user) for CRUD API
        """

        db_model = db_model or self.db_model
        if not self.request.user.is_superuser:
            filter_kwargs["owner_id"] = self.request.user.id

        instance = await db_model.async_get(self.db_session, id=instance_id, **filter_kwargs)
        if not instance:
            raise NotFoundError(
                f"{db_model.__name__} #{instance_id} does not exist or belongs to another user"
            )

        return instance

    async def _validate(
        self, request, schema: Type[Schema] = None, partial_: bool = False, location: str = None
    ) -> dict:
        """Simple validation, based on marshmallow's schemas"""

        schema_request = schema or self.schema_request
        schema_kwargs = {}
        if partial_:
            schema_kwargs["partial"] = [field for field in schema_request().fields]

        schema, cleaned_data = schema_request(**schema_kwargs), {}
        try:
            cleaned_data = await parser.parse(schema, request, location=location)
            if hasattr(schema, "is_valid") and callable(schema.is_valid):
                schema.is_valid(cleaned_data)

        except ValidationError as e:
            raise InvalidParameterError(details=e.data)

        return cleaned_data

    def _response(
        self,
        data: Union[DBModel, Iterable[DBModel], dict] = None,
        status_code: int = status.HTTP_200_OK,
        response_status: ResponseStatus = ResponseStatus.OK,
        headers: Mapping[str, str] = None,
        background: Optional[BackgroundTasks] = None,
    ) -> BaseRenderer:
        if (data is not None) and self.schema_response:
            schema_kwargs = {}
            if isinstance(data, Iterable) and not isinstance(data, dict):
                schema_kwargs["many"] = True

            payload = self.schema_response(**schema_kwargs).dump(data)
        else:
            payload = data

        # TODO: Pass only payload to renderer? Maybe pass string-like response_status independently?
        return self.renderer(
            {"status": response_status, "payload": payload},
            status_code=status_code,
            headers=headers,
            background=background,
        )
