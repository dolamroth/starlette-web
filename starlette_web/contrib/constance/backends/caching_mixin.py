from typing import Any, Callable, ByteString

from starlette_web.common.caches import caches
from starlette_web.common.conf import settings
from starlette_web.common.http.exceptions import ImproperlyConfigured
from starlette_web.contrib.constance.backends.base import BaseConstanceBackend


class ConstanceCacheMixin(BaseConstanceBackend):
    _cache_key = "default"
    _caching_timeout = None
    _preprocess_response: Callable[[ByteString], Any]

    def __init__(self):
        super().__init__()
        if self._cache_key not in settings.CACHES:
            raise ImproperlyConfigured(
                details="ConstanceCacheBackend must be configured "
                        "with existing cache_key in settings.CACHES"
            )
        self._cache = caches[self._cache_key]

    async def get(self, key: str) -> Any:
        value = self._preprocess_response(
            await self._cache.async_get(self._cache_keygen(key))
        )
        if value == self.empty:
            value = await super().get(key)
            if value != self.empty:
                await self._cache.async_set(
                    self._cache_keygen(key),
                    self.serializer.serialize(value),
                    timeout=self._caching_timeout,
                )
        return value

    async def set(self, key: str, value: Any) -> None:
        await self._cache.async_set(
            self._cache_keygen(key),
            self.serializer.serialize(value),
            timeout=self._caching_timeout,
        )
        await super().set(key, value)

    @staticmethod
    def _cache_keygen(key: str) -> str:
        return ":constance:" + key
