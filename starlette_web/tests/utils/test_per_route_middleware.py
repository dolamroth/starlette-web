import time

from starlette_web.common.caches import caches
from starlette_web.tests.core.test_base import BaseTestAPIView
from starlette_web.tests.helpers import await_


class TestPerRouteMiddleware(BaseTestAPIView):
    def test_middleware_reset_status_code(self, client, loop):
        response = client.get("/reset-status-code/")
        assert response.status_code == 201

    def test_cache_middleware(self, client, loop):
        await_(caches["default"].async_clear())

        start_time = time.monotonic()
        _ = client.get("/cachable-response/")
        end_time = time.monotonic()
        assert abs(end_time - start_time - 2.0) < 0.1

        start_time = time.monotonic()
        _ = client.get("/cachable-response/")
        end_time = time.monotonic()
        assert abs(end_time - start_time) < 0.1
