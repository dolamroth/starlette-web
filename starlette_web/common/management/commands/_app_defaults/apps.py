from starlette_web.common.conf.base_app_config import BaseAppConfig


class AppConfig(BaseAppConfig):
    app_name = "__APPNAME"

    def initialize(self):
        pass

    def perform_checks(self):
        pass
