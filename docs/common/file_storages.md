## File storages

File storages in `starlette_web` are dedicated to work with files, added by users 
(**media files** in Django terminology). 
They provide a unified mechanism for managing files, without direct access to file handlers/descriptors.

File storages explicitly separate reading and writing from each other. 
Developer is encouraged to use `storage.reader` and `storage.writer` for all read/write operations.

All supported methods are asynchronous.

### Usage

```python3
from starlette_web.common.conf import settings
from starlette_web.common.files.storages import MediaFileSystemStorage, FilesystemStorage


async with MediaFileSystemStorage() as storage:
    async with storage.reader("/path/to/file", mode="b") as _reader:
        content = await _reader.read(1024)
        line = await _reader.readline()

    async with storage.writer("/path/to/file", mode="b", append=True) as _writer:
        await _writer.write(b"12345")

async with FilesystemStorage(BASE_DIR=settings.PROJECT_ROOT_DIR / "filestorage") as storage:
    _ = await storage.get_url("/path/to/file")
    _ = await storage.get_mtime("/path/to/file")
    _ = await storage.size("/path/to/file")
    _ = await storage.delete("/path/to/file")
    _ = await storage.exists("/path/to/file")
    _ = await storage.listdir("/path/to/directory")
```

### Supported storages

- `starlette_web.common.files.storages.filesystem.FilesystemStorage`
  - Base file storage. Requires settings BASE_DIR option, and does not define `get_url` by default.
  - Actually, does synchronous FileIO by chunks with asynchronous checkpoints in-between.
    This is for multiple reasons: it is generally faster for small files, and it is safer, since
    all major async libraries just wrap synchronous FileIO in threads, which are un-cancellable by
    `anyio.CancelledError`. [This may change in the future.](https://github.com/dolamroth/starlette-web/issues/31)
  - **Important**: By default, uses `Filelock` as cross-process mutex.
    For faster access, it is recommended to subclass default implementation and provide faster 
    cross-process synchronization mechanism, if you have any (i.e. Redis Lock).
  - **Important**: By default, has `300` seconds writing timeout and `600` seconds lock-acquire timeout.
    If you need adjusting these values, subclass the storage.
- `starlette_web.common.files.storages.filesystem.MediaFileSystemStorage`
  - Inherits `FilesystemStorage`. **Recommended** way to store user files. 
    Uses `settings.MEDIA["ROOT"]` as its base directory and `settings.MEDIA["URL"]` for `get_url`.

### Implementing custom storage

To implement a custom storage, subclass `starlette_web.common.files.storages.base.BaseStorage`.

By default, `BaseStorage` wraps all operations with asynchronous dummy lock, which doesn't actually lock.
You may leave it as is, or use your cross-process asynchronous lock of choice.
The lock interface allows defining a RW-lock, though default implementation is not provided.
