import sys
from typing import Any, AnyStr, List, Literal, Optional
from typing import AsyncContextManager, AsyncIterator

import anyio

from starlette_web.common.http.exceptions import NotSupportedError


MODE = Literal["t", "b"]


class DummyAsyncLock:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> Optional[bool]:
        return False


class BaseStorage(AsyncContextManager):
    """
    >>> async with BaseStorage() as storage:
    >>>     async with storage.reader("/path/to/file", mode="b") as _reader:
    >>>         content = await _reader.read(1024)
    >>>
    >>>     async with storage.writer("/path/to/file", mode="b") as _writer:
    >>>         await _writer.write(b"12345")
    """
    EXIT_MAX_DELAY = 60
    _blocking_timeout = 600
    _write_timeout = 300
    _directory_create_mode = 0o755

    def __init__(self, **options):
        self.options = options
        self.blocking_timeout = self.options.get("blocking_timeout", self._blocking_timeout)
        self.write_timeout = self.options.get("write_timeout", self._write_timeout)
        self.directory_create_mode = self.options.get(
            "directory_create_mode", self._directory_create_mode
        )

    async def __aenter__(self) -> "BaseStorage":
        await self._connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> Optional[bool]:
        with anyio.fail_after(self.EXIT_MAX_DELAY, shield=True):
            await self._disconnect()

        return False

    def writer(self, path: str, mode: MODE = "b", append=False, **kwargs) -> "_AsyncWriter":
        return _AsyncWriter(self, path, mode, append=append, **kwargs)

    def reader(self, path: str, mode: MODE = "b", **kwargs) -> "_AsyncReader":
        return _AsyncReader(self, path, mode, **kwargs)

    async def delete(self, path: str):
        raise NotSupportedError(details="Not supported for this storage.")

    async def get_url(self, path: str) -> str:
        raise NotSupportedError(details="Not supported for this storage.")

    async def listdir(self, path: str) -> List[str]:
        raise NotSupportedError(details="Not supported for this storage.")

    async def exists(self, path: str) -> bool:
        raise NotSupportedError(details="Not supported for this storage.")

    async def size(self, path: str) -> int:
        raise NotSupportedError(details="Not supported for this storage.")

    async def get_mtime(self, path) -> float:
        raise NotSupportedError(details="Not supported for this storage.")

    # Protected methods, not to be used directly

    async def _connect(self):
        pass

    async def _disconnect(self):
        pass

    async def _open(self, path: str, mode="b", **kwargs) -> Any:
        raise NotSupportedError(details="Not supported for this storage.")

    async def _close(self, fd: Any) -> None:
        raise NotSupportedError(details="Not supported for this storage.")

    async def _write(self, fd: Any, content: AnyStr) -> None:
        raise NotSupportedError(details="Not supported for this storage.")

    async def _read(self, fd: Any, size: int = -1) -> AnyStr:
        raise NotSupportedError(details="Not supported for this storage.")

    async def _readline(self, fd: Any, size: int = -1) -> AnyStr:
        raise NotSupportedError(details="Not supported for this storage.")

    async def _finalize_read(self, fd: Any) -> None:
        pass

    async def _finalize_write(self, fd: Any) -> None:
        pass

    def get_access_lock(self, path: str, mode="r") -> AsyncContextManager:
        # Mode parameter allows possible usage of RWLock,
        # should you find a working cross-process implementation
        return DummyAsyncLock()


class _AsyncResourse(AsyncContextManager):
    def __init__(self, storage: BaseStorage, path: str, mode: str, **kwargs):
        self._storage = storage
        self._path = path
        self._mode = mode
        self._fd: Any = None
        self._kwargs = kwargs
        self._resource_lock = self._storage.get_access_lock(path, mode=mode)

        if self._mode not in ["t", "b"]:
            raise NotSupportedError(
                details="Supported modes for opening file are 't', 'b'."
            )

    async def __aenter__(self):
        _ = await self._resource_lock.__aenter__()
        self._fd = await self._storage._open(self._path, self._mode, **self._kwargs)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> Optional[bool]:
        await self.close_task()
        self._fd = None
        return False

    async def close_task(self):
        try:
            if self._fd:
                await self._storage._close(self._fd)
        finally:
            await self._resource_lock.__aexit__(*sys.exc_info())


class _AsyncWriter(_AsyncResourse):
    def __init__(self, storage: BaseStorage, path: str, mode: str, append=False, **kwargs):
        super().__init__(storage, path, mode, **kwargs)
        self._mode = ("a" if append else "w") + self._mode
        self._rollback = False

    async def write(self, content: AnyStr) -> None:
        await self._storage._write(self._fd, content)

    async def close_task(self):
        try:
            if self._fd:
                await self._storage._finalize_write(self._fd)
        finally:
            await super().close_task()


class _AsyncReader(_AsyncResourse):
    def __init__(self, storage: BaseStorage, path: str, mode: str, **kwargs):
        super().__init__(storage, path, mode, **kwargs)
        self._mode = "r" + self._mode

    async def read(self, size: int = -1) -> AnyStr:
        return await self._storage._read(self._fd, size)

    async def readline(self, size: int = -1) -> AnyStr:
        return await self._storage._readline(self._fd, size)

    async def __aiter__(self) -> AsyncIterator[AnyStr]:
        while line := (await self.readline()):
            yield line

    async def close_task(self):
        try:
            if self._fd:
                await self._storage._finalize_read(self._fd)
        finally:
            await super().close_task()
