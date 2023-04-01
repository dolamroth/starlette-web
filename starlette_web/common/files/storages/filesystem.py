import os
import sys
from pathlib import Path
from typing import List, AnyStr, AsyncContextManager, Union

import anyio
from anyio._core._fileio import AsyncFile

from starlette_web.common.conf import settings
from starlette_web.common.files.storages.base import BaseStorage, MODE
from starlette_web.common.files.filelock import FileLock
from starlette_web.common.http.exceptions import ImproperlyConfigured
from starlette_web.common.utils import urljoin


class FilesystemStorage(BaseStorage):
    def __init__(self, **options):
        super().__init__(**options)
        self.BASE_DIR = self.options.get("BASE_DIR")
        self._initialize_base_dir()

    def _initialize_base_dir(self):
        if self.BASE_DIR is None:
            raise ImproperlyConfigured(details="Storage must be inited with BASE_DIR.")

        try:
            self.BASE_DIR = Path(self.BASE_DIR)
            self.BASE_DIR.mkdir(exist_ok=True, parents=True)
        except OSError as exc:
            raise ImproperlyConfigured(details=str(exc)) from exc

    def _normalize_path(self, path: Union[str, Path]) -> anyio.Path:
        return anyio.Path(str(self.BASE_DIR / str(Path(path)).strip(os.sep)))

    async def delete(self, path: str):
        async with self.get_access_lock(path, mode="w"):
            _path = self._normalize_path(path)
            if await _path.is_dir():
                await _path.rmdir()
            elif await _path.is_file():
                await _path.unlink()

    async def listdir(self, path: str) -> List[str]:
        async with self.get_access_lock(path, mode="r"):
            _path = self._normalize_path(path)
            _paths = []
            async for path in _path.iterdir():
                _paths.append(path.name)
        return _paths

    async def exists(self, path: str) -> bool:
        async with self.get_access_lock(path, mode="r"):
            _path = self._normalize_path(path)
            return await _path.exists()

    async def size(self, path: str) -> int:
        async with self.get_access_lock(path, mode="r"):
            _path = self._normalize_path(path)
            return (await _path.stat()).st_size

    async def get_mtime(self, path) -> float:
        async with self.get_access_lock(path):
            _path = self._normalize_path(path)
            return (await _path.stat()).st_mtime

    async def _open(self, path: str, mode: MODE = "b", **kwargs) -> AsyncFile:
        _path = self._normalize_path(path)
        await self._mkdir(os.path.dirname(_path), **kwargs)
        async_file: AsyncFile = await anyio.open_file(_path, mode, **kwargs)
        return await async_file.__aenter__()

    async def _close(self, fd: AsyncFile) -> None:
        await fd.__aexit__(*sys.exc_info())

    async def _write(self, fd: AsyncFile, content: AnyStr) -> None:
        await fd.write(content)

    async def _read(self, fd: AsyncFile, size: int = -1) -> AnyStr:
        return await fd.read(size)

    async def _readline(self, fd: AsyncFile, size: int = -1) -> AnyStr:
        # TODO: buffered read (anyio AsyncFile does not support size)
        return await fd.readline()

    async def _mkdir(self, path: str, **kwargs) -> None:
        _path = self._normalize_path(path)
        mode = kwargs.pop("mode", self.directory_create_mode)
        exist_ok = kwargs.pop("exist_ok", True)
        parents = kwargs.pop("parents", True)
        await _path.mkdir(exist_ok=exist_ok, parents=parents, mode=mode)

    async def _finalize_write(self, fd: AsyncFile) -> None:
        await fd.flush()
        os.fsync(fd._fp.fileno())

    def get_access_lock(self, path: str, mode="r") -> AsyncContextManager:
        # Consider subclassing FileSystemStorage, to use
        # faster cross-process lock, i.e. Redis lock
        if mode == "w":
            _path = Path(self._normalize_path(path))
            _lockname = _path.parent / (_path.name + ".lock")

            return FileLock(
                name=str(_lockname),
                timeout=self.write_timeout,
                blocking_timeout=self.blocking_timeout,
            )
        else:
            return super().get_access_lock(path, mode)


class MediaFileSystemStorage(FilesystemStorage):
    def __init__(self, **options):
        BaseStorage.__init__(self, **options)
        self.BASE_DIR = settings.MEDIA["ROOT_DIR"]
        self._initialize_base_dir()

    async def get_url(self, path: str) -> str:
        _path = str(Path(path)).split(os.sep)
        return urljoin(settings.MEDIA["URL"], "/".join(_path))
