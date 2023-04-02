from pathlib import Path

from starlette_web.common.conf import settings
from starlette_web.common.files.storages import MediaFileSystemStorage
from starlette_web.tests.helpers import await_


class TestFileSystemStorage:
    base_dir = settings.MEDIA["ROOT_DIR"]

    def test_fetch_file_by_url(self, client):
        rel_path = "dir1/dir2/file1.txt"

        async def write_and_get_url():
            async with MediaFileSystemStorage() as storage:
                async with storage.writer(rel_path, "t") as writer:
                    await writer.write("Test content")

                return await storage.get_url(rel_path)

        url = await_(write_and_get_url())
        assert (Path(self.base_dir) / rel_path).is_file()
        assert url == "/media/dir1/dir2/file1.txt"

        response = client.get(url)
        assert response.content.decode("utf-8") == "Test content"
