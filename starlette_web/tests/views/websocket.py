import logging
from typing import Dict, Any, Optional

import anyio
from anyio.abc import TaskStatus
from marshmallow import Schema, fields
from marshmallow.validate import OneOf
from starlette.types import Scope, Receive, Send
from starlette.websockets import WebSocket, WebSocketDisconnect

from starlette_web.common.authorization.permissions import IsAuthenticatedPermission
from starlette_web.common.conf import settings
from starlette_web.common.caches import caches
from starlette_web.common.channels.base import Channel
from starlette_web.common.ws.base_endpoint import BaseWSEndpoint
from starlette_web.common.utils.crypto import get_random_string
from starlette_web.contrib.auth.backend import JWTAuthenticationBackend
from starlette_web.contrib.redis.channel_layers import RedisPubSubChannelLayer


logger = logging.getLogger("starlette_web.tests")
locmem_cache = caches["locmem"]


class WebsocketRequestSchema(Schema):
    request_type = fields.Str()


class ChatRequestSchema(Schema):
    request_type = fields.Str(
        validate=[
            OneOf(["connect", "publish"]),
        ]
    )
    message = fields.Str(required=False)


class BaseWebsocketTestEndpoint(BaseWSEndpoint):
    request_schema = WebsocketRequestSchema

    async def _background_handler(self, task_id: str, websocket: WebSocket, data: Dict):
        await anyio.sleep(2)
        return data["request_type"]

    async def _register_background_task(self, task_id: str, websocket: WebSocket, data: Dict):
        await locmem_cache.async_set(task_id, 1, timeout=20)

    async def _unregister_background_task(
        self, task_id: str, websocket: WebSocket, task_result: Any
    ):
        await locmem_cache.async_delete(task_id)
        if task_result is not None:
            await locmem_cache.async_set(task_id + "_result", task_result, timeout=20)


class CancellationWebsocketTestEndpoint(BaseWebsocketTestEndpoint):
    async def _background_handler(self, task_id: str, websocket: WebSocket, data: Dict):
        if data["request_type"] == "cancel":
            return

        if data["request_type"] == "fail":
            raise Exception("fail")

        return await super()._background_handler(task_id, websocket, data)

    async def _handle_background_task_exception(
        self, task_id: str, websocket: WebSocket, exc: Exception
    ):
        await locmem_cache.async_set(task_id + "_exception", str(exc), timeout=20)
        raise WebSocketDisconnect(code=1005) from exc


class AuthenticationWebsocketTestEndpoint(BaseWebsocketTestEndpoint):
    # Note, that authentication via "Authorization" header
    # is not supported by web-browsers' WebSocket API.
    # Instead, use custom schema, such as setting "Sec-WebSocket-Protocol" header.
    auth_backend = JWTAuthenticationBackend
    permission_classes = [IsAuthenticatedPermission]
    EXIT_MAX_DELAY = 5


class FinitePeriodicTaskWebsocketTestEndpoint(BaseWebsocketTestEndpoint):
    EXIT_MAX_DELAY = 5

    async def _background_handler(self, task_id: str, websocket: WebSocket, data: Dict):
        for i in range(4):
            await websocket.send_json({"response": i})
            await anyio.sleep(1)

        return "finished"


class InfinitePeriodicTaskWebsocketTestEndpoint(BaseWebsocketTestEndpoint):
    EXIT_MAX_DELAY = 5

    async def _background_handler(self, task_id: str, websocket: WebSocket, data: Dict):
        prefix = data["request_type"]

        i = 0
        while True:
            await websocket.send_json({"response": prefix + "_" + str(i)})
            await anyio.sleep(1)
            i += 1

    async def _unregister_background_task(
        self, task_id: str, websocket: WebSocket, task_result: Any
    ):
        await locmem_cache.async_delete(task_id)
        # Explicitly set "finished" task_result for tests
        await locmem_cache.async_set(task_id + "_result", "finished", timeout=20)


class ChatWebsocketTestEndpoint(BaseWSEndpoint):
    request_schema = ChatRequestSchema

    def __init__(self, scope: Scope, receive: Receive, send: Send) -> None:
        super().__init__(scope, receive, send)
        self._manager_lock = anyio.Lock()
        self._response_handler_init = False
        self._channels_init = False
        self._channels_wrap: Optional[Channel] = None
        self._channels: Optional[Channel] = None
        self._tasks = set()
        self._close_event: Optional[anyio.Event] = None

    async def _run_channel(
        self,
        close_event: anyio.Event,
        task_status: TaskStatus = anyio.TASK_STATUS_IGNORED,
    ):
        # Move channel management to a separate background task,
        # so that channel's anyio.TaskGroup does not interfere
        # with any other possible cancel scopes.
        # Note, that in this case it requires
        # some low-level synchronization with anyio.Event.
        # Note, as well, that this task does not add to self._tasks
        redis_options = settings.CHANNEL_LAYERS["redispubsub"]["OPTIONS"]
        async with Channel(RedisPubSubChannelLayer(**redis_options)) as channel:
            task_status.started(channel)
            await close_event.wait()

    async def _register_background_task(self, task_id: str, websocket: WebSocket, data: Dict):
        async with self._manager_lock:
            if not self._channels_init and data["request_type"] == "connect":
                self._close_event = anyio.Event()
                self._channels = await self.task_group.start(self._run_channel, self._close_event)
                self._channels_init = True

            self._tasks.add(task_id)

    async def _background_handler(self, task_id: str, websocket: WebSocket, data: Dict):
        async with self._manager_lock:
            if not self._channels_init:
                logger.debug("No initialized channels detected. Quit handler")
                return

        room = "chatroom"

        if data["request_type"] == "publish":
            await self._channels.publish(room, data["message"])

        elif data["request_type"] == "connect":
            # In test endpoint, _unregister_background_task checks that
            # there are any tasks left, before closing the channel.
            # Since this parent task will close as soon
            # it spawns dialogue task, we need to register the latter.
            dialogue_task_id = get_random_string(50)
            self._tasks.add(dialogue_task_id)
            self.task_group.start_soon(self._run_dialogue, websocket, room, dialogue_task_id)

        else:
            raise WebSocketDisconnect(code=1005, reason="Invalid request type")

    async def _unregister_background_task(
        self, task_id: str, websocket: WebSocket, task_result: Any
    ):
        async with self._manager_lock:
            self._tasks.discard(task_id)

            if self._channels_init and not self._tasks:
                self._close_event.set()
                self._channels_init = False

    async def _run_dialogue(self, websocket: WebSocket, room: str, dialogue_task_id: str):
        try:
            async with self._manager_lock:
                if self._response_handler_init:
                    return
                self._response_handler_init = True

            async with self._channels.subscribe(room) as subscriber:
                async for event in subscriber:
                    await websocket.send_json(event.message)
        finally:
            self._tasks.discard(dialogue_task_id)
            async with self._manager_lock:
                self._response_handler_init = False
