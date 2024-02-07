import anyio
from anyio.streams.memory import (
    MemoryObjectReceiveStream,
    MemoryObjectSendStream,
)
from typing import Dict, Any, Optional

from starlette_web.common.channels.event import Event
from starlette_web.common.channels.layers.base import BaseChannelLayer


class InMemoryChannelLayer(BaseChannelLayer):
    # Single-process channel layer, uses fire-and-forget scheme
    def __init__(self, max_buffer_size: int = 0, **options):
        super().__init__(**options)
        self._subscribed: Dict = dict()
        self._receive_stream: Optional[MemoryObjectReceiveStream] = None
        self._send_stream: Optional[MemoryObjectSendStream] = None
        self.max_buffer_size = max_buffer_size
        self._manager_lock = anyio.Lock()

    async def connect(self) -> None:
        self._send_stream, self._receive_stream = anyio.create_memory_object_stream(
            max_buffer_size=self.max_buffer_size,
        )

    async def disconnect(self) -> None:
        self._subscribed.clear()
        self._send_stream.close()
        self._receive_stream.close()
        self._send_stream = None
        self._receive_stream = None

    async def subscribe(self, group: str, **kwargs) -> None:
        async with self._manager_lock:
            self._subscribed.setdefault(group, 0)
            self._subscribed[group] += 1

    async def unsubscribe(self, group: str, **kwargs) -> None:
        async with self._manager_lock:
            self._subscribed.setdefault(group, 0)
            self._subscribed[group] -= 1

    async def publish(self, group: str, message: Any, **kwargs) -> None:
        if not self._send_stream:
            raise RuntimeError(".publish() requires not-null self._send_stream")

        event = Event(group=group, message=message)
        await self._send_stream.send(event)

    async def next_published(self) -> Event:
        if not self._receive_stream:
            raise RuntimeError(".next_published() requires not-null self._receive_stream")

        while True:
            event = await self._receive_stream.receive()
            if self._subscribed.get(event.group, 0) > 0:
                return event
