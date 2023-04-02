import hashlib
import os
import pickle
import tempfile
import time
from typing import Any, Union, Optional

from anyio.lowlevel import checkpoint, cancel_shielded_checkpoint
from filelock import FileLock as StrictFileLock

from starlette_web.common.conf import settings
from starlette_web.common.caches.base_lock import BaseLock, CacheLockError


class FileLock(BaseLock):
    """
    An async variation of SoftFileLock with support of timeout (via os.path.getmtime)
    """
    EXIT_MAX_DELAY = 60.0

    def __init__(
        self,
        name: Union[str, os.PathLike[Any]],
        timeout: Optional[float] = None,
        blocking_timeout: Optional[float] = None,
        **kwargs,
    ) -> None:
        super().__init__(name, timeout, blocking_timeout, **kwargs)
        self._stored_file_ts = {}

    async def _acquire(self):
        if self._is_acquired:
            return

        while True:
            await checkpoint()
            try:
                with self._get_manager_lock():
                    if self._sync_acquire():
                        self._acquire_event.set()
                        return
            except CacheLockError:
                self._task_group.cancel_scope.cancel()
                raise
            except OSError:
                continue

    async def _release(self):
        if not self._is_acquired:
            return

        while True:
            try:
                await cancel_shielded_checkpoint()
            except BaseException:  # noqa
                self._sync_release()
                raise

            try:
                with self._get_manager_lock():
                    self._sync_release()
                    return
            except OSError:
                continue

    def _sync_release(self):
        try:
            ts = os.path.getmtime(self._name)
            # Another process has re-acquired lock due to timeout
            if ts not in self._stored_file_ts:
                return
            os.unlink(self._name)
        finally:
            self._stored_file_ts = {}
            self._is_acquired = False

    def _sync_acquire(self) -> bool:
        if os.path.exists(self._name):
            ts = os.path.getmtime(self._name)

            if ts not in self._stored_file_ts:
                with open(self._name, "rb") as file:
                    try:
                        self._stored_file_ts[ts] = pickle.loads(file.read())
                    except pickle.PickleError as exc:
                        raise CacheLockError(details=str(exc)) from exc

            # Timeout on other instance has not expired
            if self._stored_file_ts[ts] + ts > time.time():
                return False

            # Timeout for lock has expired, so we acquire it.
            # Remove lock file to update its mtime
            self._sync_release()

        with open(self._name, "wb+") as file:
            file.write(pickle.dumps(self._timeout, protocol=4))
            # Guarantee that writing is finalized
            file.flush()
            os.fsync(file.fileno())

        ts = os.path.getmtime(self._name)
        self._stored_file_ts[ts] = self._timeout
        return True

    def __del__(self):
        try:
            self._sync_release()
        except OSError:
            pass

    def _get_manager_lock(self):
        _manager_lock_filepath = os.path.join(
            tempfile.gettempdir(),
            self._get_project_hash() + "_filelock.lock",
        )
        # timeout=0 means exactly 1 attempt to acquire lock
        return StrictFileLock(_manager_lock_filepath, timeout=0)

    def _get_project_hash(self):
        return hashlib.md5(str(settings.SECRET_KEY).encode('utf-8')).hexdigest()
