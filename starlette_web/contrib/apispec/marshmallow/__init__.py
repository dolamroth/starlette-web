from apispec import APISpec
from apispec.ext.marshmallow import MarshmallowPlugin

from starlette_web.contrib.apispec.marshmallow.converters import (
    StarletteWebMarshmallowOpenAPIConverter,
)


class StarletteWebMarshmallowPlugin(MarshmallowPlugin):
    Converter = StarletteWebMarshmallowOpenAPIConverter

    def init_spec(self, spec: APISpec) -> None:
        super().init_spec(spec)
        self.converter.add_attribute_function(self.converter.method2properties)
