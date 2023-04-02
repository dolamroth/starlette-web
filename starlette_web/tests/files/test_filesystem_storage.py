import time
import os
from pathlib import Path

import pytest

from starlette_web.common.conf import settings
from starlette_web.common.files.storages import FilesystemStorage
from starlette_web.tests.helpers import await_


class TestFileSystemStorage:
    base_dir = settings.FILESTORAGE_DIR

    def test_file_write(self):
        rel_path = "dir1/dir2/file1.txt"

        async def write_task():
            async with FilesystemStorage(BASE_DIR=self.base_dir) as storage:
                async with storage.writer(rel_path, "t") as writer:
                    await writer.write("Test content")

        await_(write_task())
        assert (Path(self.base_dir) / rel_path).is_file()

    def test_file_read(self):
        rel_path = "dir1/dir3/file2.txt"

        async def write_and_read_task():
            async with FilesystemStorage(BASE_DIR=self.base_dir) as storage:
                async with storage.writer(rel_path, "b") as writer:
                    await writer.write(b"Test content")

                async with storage.reader(rel_path, "b") as reader:
                    return await reader.read(4)

        value = await_(write_and_read_task())
        assert (Path(self.base_dir) / rel_path).is_file()
        assert value == b"Test"

    def test_readline(self):
        rel_path = "dir1/dir3/file5.txt"

        with open(Path(self.base_dir) / rel_path, "wb") as file:
            file.write(b"\n".join([
                (b"Line " + str(i).encode())
                for i in range(1000)
            ]))

        async def write_and_read_task():
            _lines = []

            async with FilesystemStorage(BASE_DIR=self.base_dir) as storage:
                async with storage.reader(rel_path, "b") as _reader:
                    async for line in _reader:
                        _lines.append(line)

            return _lines

        lines = await_(write_and_read_task())
        assert lines[0].strip(b"\r\n") == b"Line 0"
        assert len(lines) == 1000

    def test_file_delete(self):
        rel_path = "dir1/dir2/file4.txt"

        async def create_task():
            async with FilesystemStorage(BASE_DIR=self.base_dir) as storage:
                async with storage.writer(rel_path, "b") as writer:
                    await writer.write(b"Test content")

        await_(create_task())
        assert (Path(self.base_dir) / rel_path).is_file()
        assert (Path(self.base_dir) / "dir1").is_dir()

        async def delete_task():
            async with FilesystemStorage(BASE_DIR=self.base_dir) as storage:
                await storage.delete(rel_path)

        await_(delete_task())
        assert not (Path(self.base_dir) / rel_path).is_file()

        async def delete_directory():
            async with FilesystemStorage(BASE_DIR=self.base_dir) as storage:
                for path in (await storage.listdir("dir1/dir2")):
                    await storage.delete("dir1/dir2/" + path)

                await storage.delete("dir1/dir2")

        await_(delete_directory())
        assert not (Path(self.base_dir) / "dir1" / "dir2").is_dir()

    def test_utils_functions(self):
        rel_path = "dir1/dir3/file3.txt"
        current_time = time.time()

        async def utils_task():
            async with FilesystemStorage(BASE_DIR=self.base_dir) as storage:
                async with storage.writer(rel_path, "b") as writer:
                    await writer.write(b"Test content")

                _mtime = await storage.get_mtime(rel_path)
                _exists = await storage.exists(rel_path)
                _listdir = await storage.listdir(os.path.dirname(rel_path))
                _size = await storage.size(rel_path)

                return _mtime, _exists, _listdir, _size

        mtime, exists, listdir, size = await_(utils_task())

        assert abs(current_time - mtime) < 1.0
        assert exists
        assert "file3.txt" in listdir
        assert size == 12

    def test_cant_delete_non_empty_dir(self):
        rel_path = "dir1/dir2/file1.txt"

        async def write_and_delete_task():
            async with FilesystemStorage(BASE_DIR=self.base_dir) as storage:
                async with storage.writer(rel_path, "t") as writer:
                    await writer.write("Test content")

                await storage.delete("dir1/dir2")

        with pytest.raises(OSError):
            await_(write_and_delete_task())
