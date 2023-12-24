from starlette.responses import Response
from starlette.types import ASGIApp, Receive, Scope, Send, Message

from starlette_web.common.caches import caches


class SetResponseStatusCode201TestMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        async def _send_wrapper(message: Message):
            if "status" in message:
                message["status"] = 201
            await send(message)

        await self.app(scope, receive, _send_wrapper)


class CacheMiddleware:
    # Files cache is used in tests, because redis/locmem is fixed to event loop,
    # whereas test WebClient creates its own event loop in another thread.
    cache_name = "files"
    cache_key = "test_request"

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        assert scope["type"] == "http"

        response = await caches[self.cache_name].async_get(self.cache_key)
        if response is not None:
            await response(scope, receive, send)
            return

        async def send_with_caching(message: Message) -> None:
            _status_code = 200
            if message["type"] == "http.response.start":
                _status_code = message["status"]
                await send(message)
                return

            assert message["type"] == "http.response.body"
            response = Response(content=message["body"], status_code=_status_code)
            await caches[self.cache_name].async_set(self.cache_key, response, timeout=5.0)
            await send(message)

        await self.app(scope, receive, send_with_caching)
