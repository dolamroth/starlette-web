from pathlib import Path

from starlette_web.common.conf import settings
from starlette_web.common.files.storages import storage_manager
from starlette_web.tests.helpers import await_


class TestStorageManager:
    base_dir = settings.MEDIA["ROOT_DIR"]

    def test_storage_manager_write(self, client):
        rel_path = "dir1/dir2/file5.txt"

        async def write_and_get_url():
            await storage_manager.write(rel_path, mode="t", content="Test content")
            return await storage_manager.get_url(rel_path)

        url = await_(write_and_get_url())
        assert (Path(self.base_dir) / rel_path).is_file()
        assert url == "/media/dir1/dir2/file5.txt"

        response = client.get(url)
        assert response.content.decode("utf-8") == "Test content"

    def test_storage_manager_read(self):
        rel_path = "dir1/dir2/file6.txt"
        fullpath = Path(self.base_dir) / rel_path
        with open(fullpath, "wb") as file:
            file.write(b"Test storage manager read")

        content = await_(storage_manager.read(rel_path))
        assert content == b"Test storage manager read"
