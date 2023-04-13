from collections import OrderedDict
from importlib import import_module

from starlette_web.common.conf import settings
from starlette_web.common.conf.base_app_config import BaseAppConfig
from starlette_web.common.http.exceptions import ImproperlyConfigured


class AppManager:
    """
    A project-wide manager for installed modules (apps, in django terminology).
    Dynamically introspects %module_name%/apps.py and runs apps' own
    initializations and checks. Called at Starlette app initialization.
    """

    def __init__(self):
        self.app_configs: OrderedDict[str, BaseAppConfig] = OrderedDict()
        self.app_names: OrderedDict[str, str] = OrderedDict()
        self._apps_registered = False

    def register_apps(self):
        if self._apps_registered:
            return

        for installed_app in settings.INSTALLED_APPS:
            _module = import_module(installed_app)
            if not _module.__file__:
                raise ImproperlyConfigured(
                    details=f"App {installed_app} must contain an __init__.py file."
                )

            try:
                _app_module = import_module(installed_app + ".apps")
            except (SystemError, ImportError) as exc:
                raise ImproperlyConfigured(details=str(exc)) from exc

            try:
                AppConfig = getattr(_app_module, "AppConfig")
                if BaseAppConfig not in AppConfig.__mro__:
                    raise AssertionError
            except (AttributeError, AssertionError) as exc:
                raise ImproperlyConfigured(
                    details=f"App {installed_app} must define apps.AppConfig class, inherited "
                    f"from starlette_web.common.conf.base_app_config.BaseAppConfig"
                ) from exc

            app_config: BaseAppConfig = AppConfig()
            if app_config.app_name in self.app_names.keys():
                raise ImproperlyConfigured(
                    details=f"Duplicate app name {app_config.app_name}: "
                    f"{installed_app} and {self.app_names[app_config.app_name]}"
                )

            for requirement in app_config.app_requirements:
                if requirement not in self.app_names.values():
                    raise ImproperlyConfigured(
                        details=f"App {installed_app} requires {requirement} "
                        f"to be defined in settings.INSTALLED_APPS strictly before it."
                    )

            self.app_names[app_config.app_name] = installed_app
            self.app_configs[installed_app] = app_config

        self._apps_registered = True

    def initialize_apps(self):
        self.register_apps()
        for app_config in self.app_configs.values():
            app_config.initialize()

    def run_apps_checks(self):
        self.register_apps()
        for app_config in self.app_configs.values():
            app_config.perform_checks()

    def import_models(self):
        self.register_apps()
        for installed_app in settings.INSTALLED_APPS:
            try:
                import_module(installed_app + ".models")
            except (SystemError, ImportError):
                pass


app_manager = AppManager()
