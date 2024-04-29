from typing import Union, Type

from marshmallow import schema, fields

_allowed_types = Union[
    schema.Schema,
    Type[schema.Schema],
    fields.Field,
    Type[fields.Field],
]


def apispec_method_decorator(_schema_or_field: _allowed_types):
    def decorator(method_func):
        method_func._apispec_schema = _schema_or_field
        return method_func
    return decorator
