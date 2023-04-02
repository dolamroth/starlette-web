import os
from typing import Type

from starlette_web.common.conf import settings
from starlette_web.common.http.exceptions import ImproperlyConfigured
from starlette_web.common.utils.importing import import_string
from starlette_web.contrib.scheduler.backends.base import BasePeriodicTaskScheduler


def get_periodic_scheduler_backend_class() -> Type[BasePeriodicTaskScheduler]:
    try:
        backend_klass = settings.PERIODIC_JOBS_BACKEND
    except (ImproperlyConfigured, AssertionError):
        backend_klass = None

    if backend_klass is not None:
        return import_string(backend_klass)

    if os.name == "nt":
        return import_string("starlette_web.contrib.scheduler.backends.win32.WindowsTaskScheduler")

    return import_string("starlette_web.contrib.scheduler.backends.posix.CrontabScheduler")
