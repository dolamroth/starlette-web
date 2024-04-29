import json

from apispec.ext.marshmallow import OpenAPIConverter
from apispec.ext.marshmallow.field_converter import DEFAULT_FIELD_MAPPING
from marshmallow import fields, schema

from starlette_web.common.conf import settings
from starlette_web.common.utils.json import StarletteJSONEncoder
from starlette_web.contrib.camel_case.utils import camelize, camelize_key


# TODO: maybe allow user to override class in settings (?)
class StarletteWebMarshmallowOpenAPIConverter(OpenAPIConverter):
    # Decimal has no specific representation in OpenAPI standard
    # Support decimal representation in a same way, as drf-yasg does for Django
    # https://github.com/axnsan12/drf-yasg/blob/b99306f71c6a5779b62189df7d9c1f5ea1c794ef/src/drf_yasg/openapi.py#L48  # noqa: E501
    field_mapping = {
        **DEFAULT_FIELD_MAPPING,
        fields.Decimal: ("string", "decimal"),
        fields.Method: (None, None),
    }

    def field2choices(self, field, **kwargs):
        res = super().field2choices(field, **kwargs)
        return json.loads(StarletteJSONEncoder().encode(res))

    def fields2jsonschema(self, fields, *, partial=None):
        res = super().fields2jsonschema(fields, partial=partial)

        if settings.APISPEC["CONVERT_TO_CAMEL_CASE"]:
            if "required" in res and type(res["required"]) is list:
                res["required"] = [camelize_key(d) for d in res["required"]]
            if res.get("properties"):
                res["properties"] = camelize(res["properties"])
            return camelize(res)

        return res

    def method2properties(self, field: fields.Field, ret=None):
        if isinstance(field, fields.Method):
            if field._serialize_method is not None:
                if hasattr(field._serialize_method, "_apispec_schema"):
                    field_or_schema = field._serialize_method._apispec_schema
                    if isinstance(field_or_schema, type):
                        field_or_schema = field_or_schema()

                    if isinstance(field_or_schema, fields.Field):
                        ret = self.field2property(field_or_schema)
                    elif isinstance(field_or_schema, schema.Schema):
                        ret = self.resolve_nested_schema(field_or_schema)

            if field._deserialize_method is not None:
                if hasattr(field._deserialize_method, "_apispec_schema"):
                    field_or_schema = field._deserialize_method._apispec_schema
                    if isinstance(field_or_schema, type):
                        field_or_schema = field_or_schema()

                    if isinstance(field_or_schema, fields.Field):
                        ret = self.field2property(field_or_schema)
                    elif isinstance(field_or_schema, schema.Schema):
                        ret = self.resolve_nested_schema(field_or_schema)

        return ret
