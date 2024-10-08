import logging
import sys
from contextlib import AsyncExitStack
from typing import ClassVar, Type, Any, Optional, List, Dict, Tuple

import anyio
from anyio._core._tasks import TaskGroup
from marshmallow import Schema, ValidationError
from starlette.endpoints import WebSocketEndpoint
from starlette.types import Scope, Receive, Send
from starlette.websockets import WebSocket, WebSocketDisconnect

from starlette_web.common.app import WebApp
from starlette_web.common.authorization.backends import (
    BaseAuthenticationBackend,
    NoAuthenticationBackend,
)
from starlette_web.common.authorization.base_user import BaseUserMixin, AnonymousUser
from starlette_web.common.authorization.permissions import PermissionType
from starlette_web.common.http.exceptions import (
    PermissionDeniedError,
    AuthenticationFailedError,
)
from starlette_web.common.utils.crypto import get_random_string


logger = logging.getLogger(__name__)


class BaseWSEndpoint(WebSocketEndpoint):
    auth_backend: ClassVar[Type[BaseAuthenticationBackend]] = NoAuthenticationBackend
    permission_classes: ClassVar[List[PermissionType]] = []
    request_schema: ClassVar[Type[Schema]]
    user: BaseUserMixin
    task_group: Optional[TaskGroup]
    EXIT_MAX_DELAY: float = 60
    encoding = "json"

    def __init__(self, scope: Scope, receive: Receive, send: Send) -> None:
        super().__init__(scope, receive, send)
        self.task_group = None
        self.app: WebApp = self.scope.get("app")

    async def dispatch(self) -> None:
        async with anyio.create_task_group() as self.task_group:
            await super().dispatch()

    def _auth_requires_database(self):
        return (
            self.auth_backend.requires_database
            or any([
                permission_class.requires_database
                for permission_class in self.permission_classes
            ])
        )

    async def _remove_auth_db_session(self, websocket: WebSocket):
        del websocket.state.db_session

    async def on_connect(self, websocket: WebSocket) -> None:
        try:
            auth_requires_db = self._auth_requires_database()
            async with AsyncExitStack() as db_stack:
                if auth_requires_db:
                    db_session = await db_stack.enter_async_context(self.app.session_maker())
                    websocket.state.db_session = db_session

                    # Explicitly clear db_session,
                    # so that user does not use it through lengthy websocket life-state
                    db_stack.push_async_callback(self._remove_auth_db_session, websocket)

            async with self.app.session_maker() as db_session:
                websocket.state.db_session = db_session
                self.user = await self._authenticate(websocket)
                permitted, reason = await self._check_permissions(websocket)
        except Exception as exc:  # pylint: disable=broad-except
            # Any exception must be re-raised to WebSocketDisconnect
            # Otherwise, websocket will hang out,
            # since accept()/close() have not been called
            raise WebSocketDisconnect(code=1006, reason=str(exc)) from exc

        if permitted:
            await self.accept(websocket)
        else:
            raise WebSocketDisconnect(code=3000, reason=reason)

    async def accept(self, websocket: WebSocket) -> None:
        await websocket.accept()

    async def on_receive(self, websocket: WebSocket, data: Any) -> None:
        cleaned_data = self._validate(data)
        task_id = get_random_string(50)
        self.task_group.start_soon(self._background_handler_wrap, task_id, websocket, cleaned_data)

    async def on_disconnect(self, websocket: WebSocket, close_code: int) -> None:
        if self.task_group:
            if sys.exc_info() == (None, None, None):
                self.task_group.cancel_scope.cancel()
                logger.debug("TaskGroup has been explicitly cancelled.")
            else:
                logger.debug("TaskGroup will be implicitly cancelled due to exception.")

        logger.debug("WS connection has been closed.")

    async def _background_handler_wrap(self, task_id: str, websocket: WebSocket, data: Dict):
        task_result = None

        with anyio.CancelScope() as cancel_scope:
            await self._register_background_task(task_id, websocket, data)

            try:
                try:
                    task_result = await self._background_handler(task_id, websocket, data)
                except anyio.get_cancelled_exc_class() as exc:
                    logger.debug(f"Background task {task_id} has been cancelled.")
                    # As per anyio documentation, CancelError must be always re-raised.
                    # Note, that it will also cancel all other tasks.
                    raise exc
                except Exception as exc:  # pylint: disable=broad-except
                    await self._handle_background_task_exception(task_id, websocket, exc)
                finally:
                    cancel_scope.deadline = anyio.current_time() + self.EXIT_MAX_DELAY
                    cancel_scope.shield = True
            finally:
                await self._unregister_background_task(task_id, websocket, task_result)

    async def _handle_background_task_exception(
        self, task_id: str, websocket: WebSocket, exc: Exception
    ):
        error_message = "Couldn't finish _background_handler for class %s"
        error_message_message_args = (self.__class__.__name__,)
        logger.exception(error_message, *error_message_message_args)

        # By default, an exception is propagated to the parent TaskGroup,
        # causing an inner CancelScope to cancel all child tasks.
        # If this is not an expected behavior, you may silence this error.
        raise WebSocketDisconnect(code=1005, reason=str(exc)) from exc

    async def _register_background_task(self, task_id: str, websocket: WebSocket, data: Dict):
        # This method is to be redefined in child classes
        pass

    async def _unregister_background_task(
        self, task_id: str, websocket: WebSocket, task_result: Any
    ):
        # This method is to be redefined in child classes
        pass

    async def _background_handler(self, task_id: str, websocket: WebSocket, data: Dict) -> Any:
        raise WebSocketDisconnect(
            code=1005,
            reason="Background handler for Websocket is not implemented",
        )

    def _validate(self, request_data: dict) -> dict:
        try:
            return self.request_schema().load(request_data)
        except ValidationError as exc:
            # TODO: check that details is str / flatten
            raise WebSocketDisconnect(
                code=1007,
                reason=exc.data,
            ) from exc

    async def _authenticate(self, websocket: WebSocket) -> BaseUserMixin:
        backend = self.auth_backend(websocket, self.scope)
        try:
            user = await backend.authenticate()
        except AuthenticationFailedError:
            user = AnonymousUser()
        self.scope["user"] = user
        return user

    async def _check_permissions(self, websocket: WebSocket) -> Tuple[bool, str]:
        for permission_class in self.permission_classes:
            try:
                has_permission = await permission_class().has_permission(websocket, self.scope)
                if not has_permission:
                    return False, PermissionDeniedError.message
            except PermissionDeniedError as exc:
                return False, str(exc)

        return True, ""
