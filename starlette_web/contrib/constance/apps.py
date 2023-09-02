from starlette_web.common.conf import settings
from starlette_web.common.conf.base_app_config import BaseAppConfig
from starlette_web.common.http.exceptions import BaseApplicationError, ImproperlyConfigured


class AppConfig(BaseAppConfig):
    app_name = "constance"
    _error_message = (
        "settings.CONSTANCE_CONFIG must be of type " "Dict[str, Tuple[Any, str, Type]]."
    )

    def perform_checks(self):
        try:
            config = settings.CONSTANCE_CONFIG
        except (AttributeError, BaseApplicationError):
            config = {}

        self._run_config_checks(config)

    def _run_config_checks(self, _config):
        try:
            assert type(_config) == dict

            for key, value in _config.items():
                assert type(key) == str
                actual_value, description, value_type = value
                assert isinstance(value_type, type)
                assert isinstance(actual_value, value_type)
                assert type(description) == str
        except AssertionError:
            raise ImproperlyConfigured(details=self._error_message)
