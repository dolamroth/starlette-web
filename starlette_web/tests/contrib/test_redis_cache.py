import time

import anyio

from starlette_web.common.caches import caches
from starlette_web.tests.core.helpers.base_cache_tester import BaseCacheTester
from starlette_web.tests.helpers import await_


class TestRedisCache(BaseCacheTester):
    def test_redis_cache_base_ops(self):
        self._run_base_cache_test(caches["default"])

    def test_redis_cache_many_ops(self):
        self._run_cache_many_ops_test(caches["default"])

    def test_redis_lock(self):
        self._run_cache_lock_test(caches["default"])

    def test_redis_lock_race_condition(self):
        self._run_cache_mutual_lock_test(caches["default"])

    def test_redis_lock_correct_task_blocking(self):
        self._run_locks_timeouts_test(caches["default"])

    def test_redis_lock_cancellation(self):
        async def task_lock_cancel():
            with anyio.move_on_after(0.1):
                async with caches["default"].lock("test_lock_cancel", timeout=100, blocking_timeout=2):
                    await anyio.sleep(100)

        start_time = time.time()
        await_(task_lock_cancel())
        end_time = time.time()
        run_time = end_time - start_time
        assert (run_time - 0.1) < 0.05

        key = await_(caches["default"].async_get("test_lock_cancel"))
        assert key is None
