import anyio

from redis import asyncio as aioredis
from redis.asyncio.lock import Lock as AioredisLock

from starlette_web.common.caches.base import CacheLockError


class RedisLock(AioredisLock):
    EXIT_MAX_DELAY: float = 60

    async def __aenter__(self):
        try:
            return await super().__aenter__()
        except aioredis.RedisError as exc:
            raise CacheLockError from exc

    async def __aexit__(self, *args):
        try:
            # Do not raise exception, if lock has been released
            # (might have been released due to timeout)
            expected_token = self.local.token
            if expected_token is not None:
                self.local.token = None

                async def close_task():
                    await self.lua_release(
                        keys=[self.name],
                        args=[expected_token],
                        client=self.redis,
                    )

                with anyio.fail_after(self.EXIT_MAX_DELAY, shield=True):
                    await close_task()
        except (aioredis.RedisError, TimeoutError) as exc:
            raise CacheLockError from exc
