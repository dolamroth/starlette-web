from referencing.exceptions import PointerToNowhere
from traceback_with_variables import format_exc

from starlette_web.common.conf import settings
from starlette_web.common.conf.base_app_config import BaseAppConfig
from starlette_web.common.http.exceptions import ImproperlyConfigured
from starlette_web.common.utils import import_string
from starlette_web.contrib.apispec.views import schemas


class AppConfig(BaseAppConfig):
    app_name = "apispec"

    def initialize(self):
        try:
            __import__("openapi_spec_validator")
        except (SystemError, ImportError):
            raise ImproperlyConfigured(
                details=(
                    "Extra dependency 'openapi_spec_validator' is required"
                    " for starlette_web.contrib.apispec "
                    "Install it via 'pip install starlette-web[apispec]'."
                )
            )

    def perform_checks(self):
        from openapi_spec_validator import validate
        from openapi_spec_validator.validation.exceptions import (
            OpenAPIValidationError,
            OpenAPISpecValidatorError,
        )

        routes = import_string(settings.ROUTES)

        try:
            # This check mostly fails on invalid indentation
            # or partially missing properties.
            api_spec = schemas.get_schema(routes)
        except Exception as exc:  # noqa
            # Printing variable values in traceback is the only
            # viable way to know which schema is fallible
            raise ImproperlyConfigured(
                message="Invalid schema in apispec",
                details=format_exc(exc, num_skipped_frames=0),
            )

        try:
            # This check finds missing whole blocks,
            # i.e. missing info about path parameter in schema
            validate(api_spec)
        except (OpenAPIValidationError, OpenAPISpecValidatorError) as exc:
            raise ImproperlyConfigured(details=str(exc))
        except PointerToNowhere as exc:
            _str_exc = str(exc).split(" ")
            if _str_exc[1:4] == ['does', 'not', 'exist']:
                _name = _str_exc[0]
                if _name.startswith("'/components/schemas/") and _name.endswith("'"):
                    _name = _name[21:-1]
                    from marshmallow.class_registry import get_class
                    _klass_list = get_class(_name, all=True)
                    if type(_klass_list) is list and len(_klass_list) > 1:
                        pass
                    else:
                        _klass_list = []
                else:
                    _klass_list = []

                error_description = (
                    f"Schema component {_str_exc[0]} cannot be found in OpenAPI schema. "
                    f"This is most likely caused by creating multiple subclasses of "
                    f"marshmallow.schema.Schema with same class name. "
                    f"Ensure that all classes have unique names."
                )

                if _klass_list:
                    error_description += "\nDetected schemas with same class name:\n" + "\n".join([
                        f"{kls.__module__}.{kls.__name__}" for kls in _klass_list
                    ])

                raise ImproperlyConfigured(details=error_description) from exc
            else:
                raise ImproperlyConfigured(details=str(exc)) from exc
