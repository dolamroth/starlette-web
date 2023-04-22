from typing import AnyStr, List

from starlette_web.common.conf import settings
from starlette_web.common.files.storages.base import BaseStorage
from starlette_web.common.utils import import_string


class _StorageManager:
    def __init__(self):
        self._storages = {}

    def _get_storage(self, storage_name: str) -> BaseStorage:
        if storage_name in self._storages:
            return self._storages[storage_name]

        _conf = settings.STORAGES[storage_name]
        self._storages[storage_name] = import_string(_conf["BACKEND"])(
            **_conf.get("OPTIONS", {}),
        )
        return self._storages[storage_name]

    async def read(self, path: str, using="default", **kwargs) -> AnyStr:
        async with self._get_storage(using) as storage:
            async with storage.reader(path=path, **kwargs) as reader:
                return await reader.read()

    async def write(self, path: str, content: AnyStr = b"", using="default", **kwargs):
        async with self._get_storage(using) as storage:
            async with storage.writer(path=path, append=False, **kwargs) as writer:
                return await writer.write(content)

    async def append(self, path: str, content: AnyStr = b"", using="default", **kwargs):
        async with self._get_storage(using) as storage:
            async with storage.writer(path=path, append=True, **kwargs) as writer:
                return await writer.write(content)

    async def delete(self, path: str, using="default"):
        async with self._get_storage(using) as storage:
            return await storage.delete(path)

    async def get_url(self, path: str, using="default") -> str:
        async with self._get_storage(using) as storage:
            return await storage.get_url(path)

    async def listdir(self, path: str, using="default") -> List[str]:
        async with self._get_storage(using) as storage:
            return await storage.listdir(path)

    async def exists(self, path: str, using="default") -> bool:
        async with self._get_storage(using) as storage:
            return await storage.exists(path)

    async def size(self, path: str, using="default") -> int:
        async with self._get_storage(using) as storage:
            return await storage.size(path)

    async def get_mtime(self, path: str, using="default") -> float:
        async with self._get_storage(using) as storage:
            return await storage.get_mtime(path)


storage_manager = _StorageManager()
