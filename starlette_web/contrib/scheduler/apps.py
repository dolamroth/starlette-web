import json

from starlette_web.common.conf import settings as project_settings
from starlette_web.common.conf.base_app_config import BaseAppConfig
from starlette_web.common.http.exceptions import ImproperlyConfigured
from starlette_web.contrib.scheduler.app_settings import Settings
from starlette_web.contrib.scheduler.backends.base import JobType


class AppConfig(BaseAppConfig):
    app_name = "scheduler"

    def initialize(self):
        try:
            __import__("croniter")
        except (ImportError, SystemError):
            raise ImproperlyConfigured(
                details=(
                    "Extra dependency 'croniter' is required for "
                    "starlette_web.contrib.scheduler "
                    "Install it via 'pip install starlette-web[scheduler]'."
                )
            )

    def perform_checks(self):
        import croniter
        from croniter.croniter import CroniterError

        jobs_list = Settings(project_settings).PERIODIC_JOBS

        for job in jobs_list:
            try:
                json.JSONEncoder(sort_keys=True).encode(job)
            except (TypeError, ValueError) as exc:
                raise ImproperlyConfigured(
                    message=f"Cannot json-encode job {job}",
                    details=str(exc),
                ) from exc

            try:
                assert len(job) == 5
            except AssertionError:
                raise ImproperlyConfigured(
                    details=f"Required periodic job format in settings: {JobType}",
                )

            if job[0] != "@reboot":
                # If not @reboot, crontab pattern must be of specific form "[0] [1] [2] [3] [4]"
                # Here cron generator is created, and we yield 1 element
                # to initialize the pattern check inside croniter-lib
                try:
                    next(croniter.croniter(job[0]))
                except CroniterError as exc:
                    raise ImproperlyConfigured(details=str(exc)) from exc
