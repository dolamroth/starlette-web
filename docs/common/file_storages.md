## File storages

File storages in `starlette_web` are dedicated to work with files, added by users 
(**media files** in Django terminology). 
They provide a unified mechanism for managing files, without direct access to file handlers/descriptors.

File storages explicitly separate reading and writing from each other. 
Developer is encouraged to use `storage.reader` and `storage.writer` for all read/write operations.

All supported methods are asynchronous.

### Usage

Configure variable `settings.STORAGES` (default storage is automatically set to `MediaFileSystemStorage`):

```python
STORAGES = {
  "default": {
    "BACKEND": "starlette_web.common.files.storages.MediaFileSystemStorage",
  },
  "other_storage": {
    "BACKEND": "...",
    "OPTIONS": {...},
  }
}
```

Then, use it with `storage_manager`:

```python
from starlette_web.common.files.storages import storage_manager

await storage_manager.write("dir1/dir2/file5.txt", mode="t", content="Test content")
content = await storage_manager.read("dir1/dir2/file5.txt", mode="t")
file_url = await storage_manager.get_url("dir1/dir2/file5.txt")
```

For full list of methods, see next section.

### Low-level usage

```python3
from typing import List

from starlette_web.common.conf import settings
from starlette_web.common.files.storages import MediaFileSystemStorage, FilesystemStorage


async with MediaFileSystemStorage() as storage:
    async with storage.reader("/path/to/file", mode="b") as _reader:
        content = await _reader.read(1024)
        line = await _reader.readline()
        async for line in _reader:
            ...

    async with storage.writer("/path/to/file", mode="b", append=True) as _writer:
        await _writer.write(b"12345")

async with FilesystemStorage(BASE_DIR=settings.PROJECT_ROOT_DIR / "filestorage") as storage:
    url: str         = await storage.get_url("/path/to/file")
    mtime: float     = await storage.get_mtime("/path/to/file")
    size: int        = await storage.size("/path/to/file")
    _                = await storage.delete("/path/to/file")
    exists: bool     = await storage.exists("/path/to/file")
    files: List[str] = await storage.listdir("/path/to/directory")
```

### Supported storages

- `starlette_web.common.files.storages.filesystem.FilesystemStorage`
  - Base file storage. Requires settings BASE_DIR option, and does not define `get_url` by default.
  - Wraps synchronous FileIO with `anyio.to_thread.run_sync`, following 
    [recommendation of Nathaniel Smith](https://trio.readthedocs.io/en/stable/reference-io.html#background-why-is-async-file-i-o-useful-the-answer-may-surprise-you).
    However, actual implementation [may be improved in the future.](https://github.com/dolamroth/starlette-web/issues/31)
  - **Important**: By default, uses asynchronous `Filelock` as cross-process mutex.
    For faster access, it is recommended to subclass default implementation and provide faster 
    cross-process synchronization mechanism, if you have any (i.e. AioRedis Lock).
- `starlette_web.common.files.storages.filesystem.MediaFileSystemStorage`
  - Inherits `FilesystemStorage`. **Recommended** way to store user files. 
    Uses `settings.MEDIA["ROOT"]` as its base directory and `settings.MEDIA["URL"]` for `get_url`.

### Implementing custom storage

To implement a custom storage, subclass `starlette_web.common.files.storages.base.BaseStorage`.

By default, `BaseStorage` wraps all operations with asynchronous dummy lock, which doesn't actually lock.
You may leave it as is, or use your cross-process asynchronous lock of choice.
The lock interface allows defining a RW-lock, though default implementation is not provided.

Available input arguments for `FilesystemStorage`:  
- blocking_timeout: float (default `600`) - timeout to acquire lock for reading/writing, in seconds
- write_timeout: float (default: `300`) - lock expiration timeout for writing, in seconds
- directory_create_mode: int (default: `0o755`) - octal permissions for `mkdir`
- chunk_size: int (default: `65536`) - chunk size for reading/writing, in bytes
