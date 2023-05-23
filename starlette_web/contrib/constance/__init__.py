from typing import Any, List, Dict

from starlette_web.common.conf import settings
from starlette_web.common.http.exceptions import (
    NotSupportedError,
    BaseApplicationError,
    UnexpectedError,
    ImproperlyConfigured,
)
from starlette_web.common.utils import import_string
from starlette_web.contrib.constance.backends.base import BaseConstanceBackend
from starlette_web.contrib.constance.backends.caching_mixin import ConstanceCacheMixin


# TODO: some kind of validation system, much like django.checks
# TODO: _validate method
class LazyConstance:
    _backend: BaseConstanceBackend
    _is_setup: bool

    def __init__(self):
        self._is_setup = False

    async def get(self, key: str) -> Any:
        self._setup()

        if key not in settings.CONSTANCE_CONFIG:
            raise NotSupportedError(
                details=f"Key {key} is not defined in settings.CONSTANCE_CONFIG."
            )

        value = await self._backend.get(key)
        return self._postprocess_value(key, value)

    async def set(self, key: str, value: Any) -> None:
        self._setup()

        if key not in settings.CONSTANCE_CONFIG:
            raise NotSupportedError(
                details=f"Key {key} is not defined in settings.CONSTANCE_CONFIG."
            )

        expected_type = settings.CONSTANCE_CONFIG[key][2]
        if type(value) != expected_type:
            try:
                # This is for cases like int-float, str-int and such
                value = expected_type(value)
            except (TypeError, ValueError) as exc:
                raise NotSupportedError(details=str(exc))
            except Exception as exc:
                # I.e. if we try to pass datetime to uuid value, which causes OverflowError
                raise UnexpectedError(details=str(exc))

        await self._backend.set(key, value)

    async def mget(self, keys: List[str]) -> Dict[str, Any]:
        self._setup()

        if not keys:
            return {}

        for key in keys:
            if key not in settings.CONSTANCE_CONFIG:
                raise NotSupportedError(
                    details=f"Key {key} not present in settings.CONSTANCE_CONFIG."
                )

        return_list = await self._backend.mget(keys)
        return {
            key: self._postprocess_value(key, value)
            for key, value in return_list.items()
        }

    def _postprocess_value(self, key, value):
        if key not in settings.CONSTANCE_CONFIG:
            raise NotSupportedError(details=f"Key {key} not present in settings.CONSTANCE_CONFIG.")

        if value == self._backend.empty:
            return settings.CONSTANCE_CONFIG[key][0]

        return value

    def _setup(self) -> None:
        if self._is_setup:
            return

        try:
            _import_path = settings.CONSTANCE_BACKEND
            if _import_path is None:
                _backend_kls = None
            else:
                _backend_kls = import_string(_import_path)
        except (AttributeError, BaseApplicationError):
            _backend_kls = None
        except (ImportError, SystemError):
            raise ImproperlyConfigured(
                details=f"Invalid constance class: {settings.CONSTANCE_BACKEND}"
            )

        try:
            _cache_key = settings.CONSTANCE_DATABASE_CACHE_BACKEND
        except (AttributeError, BaseApplicationError):
            _cache_key = None

        if _backend_kls:
            if _cache_key:
                self._backend = type(
                    _backend_kls.__name__,
                    (ConstanceCacheMixin, _backend_kls),
                    {"_cache_key": _cache_key},
                )()
            else:
                self._backend = _backend_kls()

        self._is_setup = True


config = LazyConstance()
