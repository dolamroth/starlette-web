import math
import os
import sys
from pathlib import Path
from typing import List, AnyStr, AsyncContextManager, Union
from io import BufferedReader, TextIOWrapper, StringIO, BytesIO

from anyio.lowlevel import checkpoint

from starlette_web.common.conf import settings
from starlette_web.common.files.storages.base import BaseStorage, MODE
from starlette_web.common.files.filelock import FileLock
from starlette_web.common.http.exceptions import ImproperlyConfigured
from starlette_web.common.utils import urljoin


FDType = Union[BufferedReader, TextIOWrapper]


class FilesystemStorage(BaseStorage):
    blocking_timeout = 600
    write_timeout = 300
    directory_create_mode = 0o755
    chunk_size = 64 * 1024

    def __init__(self, **options):
        super().__init__(**options)
        self.BASE_DIR = Path(self.options.get("BASE_DIR"))
        self._initialize_base_dir()

    def _initialize_base_dir(self):
        if self.BASE_DIR is None:
            raise ImproperlyConfigured(
                details="Storage must be inited with BASE_DIR."
            )

        try:
            self.BASE_DIR.mkdir(exist_ok=True)
        except OSError as exc:
            raise ImproperlyConfigured(details=str(exc)) from exc

    def _normalize_path(self, path: Union[str, Path]) -> str:
        return str(self.BASE_DIR / str(Path(path)).strip(os.sep))

    async def delete(self, path: str):
        _path = self._normalize_path(path)
        async with self.get_access_lock(_path, mode="w"):
            _p = Path(_path)
            if _p.is_dir():
                _p.rmdir()
            elif _p.is_file():
                _p.unlink()

    async def listdir(self, path: str) -> List[str]:
        _path = self._normalize_path(path)
        async with self.get_access_lock(_path, mode="r"):
            _paths = []
            for path in Path(_path).iterdir():
                _paths.append(path.name)
        return _paths

    async def exists(self, path: str) -> bool:
        _path = self._normalize_path(path)
        async with self.get_access_lock(_path, mode="r"):
            return Path(_path).exists()

    async def size(self, path: str) -> int:
        _path = self._normalize_path(path)
        async with self.get_access_lock(_path, mode="r"):
            return Path(_path).stat().st_size

    async def get_mtime(self, path) -> float:
        _path = self._normalize_path(path)
        async with self.get_access_lock(_path):
            return Path(_path).stat().st_mtime

    async def _open(self, path: str, mode: MODE = "b", **kwargs) -> FDType:
        _path = self._normalize_path(path)
        await self._mkdir(os.path.dirname(_path), **kwargs)
        return open(_path, mode, **kwargs).__enter__()

    async def _close(self, fd: FDType) -> None:
        fd.__exit__(*sys.exc_info())

    async def _write(self, fd: FDType, content: AnyStr) -> None:
        _wrap = StringIO if type(content) == str else BytesIO
        _content = _wrap(content)
        while _chunk := _content.read(self.chunk_size):
            await checkpoint()
            fd.write(_chunk)

    async def _read(self, fd: FDType, size: int = -1) -> AnyStr:
        if -1 < size <= self.chunk_size:
            return fd.read(size)

        buffer = StringIO() if type(fd) == TextIOWrapper else BytesIO()
        _remain = size if size > 0 else math.inf
        _to_read = min([self.chunk_size, _remain])
        while _chunk := fd.read(_to_read):
            await checkpoint()
            buffer.write(_chunk)

        buffer.seek(0)
        return buffer.read()

    async def _readline(self, fd: FDType, size: int = -1) -> AnyStr:
        # TODO: support buffered read
        return fd.readline(size)

    async def _mkdir(self, path: str, **kwargs) -> None:
        _path = self._normalize_path(path)
        mode = kwargs.pop("mode", self.directory_create_mode)
        exist_ok = kwargs.pop("exist_ok", True)
        parents = kwargs.pop("parents", True)
        Path(_path).mkdir(exist_ok=exist_ok, parents=parents, mode=mode)

    async def _finalize_write(self, fd: FDType) -> None:
        fd.flush()
        os.fsync(fd.fileno())

    def get_access_lock(self, path: str, mode="r") -> AsyncContextManager:
        # Consider subclassing FileSystemStorage, to use
        # faster cross-process lock, i.e. Redis lock
        if mode == "w":
            return FileLock(
                name=str(Path(path)).strip(os.sep).replace(os.sep, "_"),
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
        _path = path.split(os.sep)
        return urljoin(settings.MEDIA["URL"], "/".join(_path))
