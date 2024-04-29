import uuid
import random
from typing import List

from marshmallow import schema, fields

from starlette_web.contrib.apispec.utils import apispec_method_decorator


class ServicesCheckSchema(schema.Schema):
    postgres = fields.Str()


class HealthCheckSchema(schema.Schema):
    services = fields.Nested(ServicesCheckSchema)
    errors = fields.List(fields.Str)


class EndpointWithContextRequestSchema(schema.Schema):
    value = fields.Method(None, "get_value")

    def get_value(self, value):
        return value + self.context.get("add", 0)


class EndpointWithContextResponseSchema(schema.Schema):
    value = fields.Method("get_value", None)

    def get_value(self, obj):
        return obj.get("value", 0) ** 2 + self.context.get("add", 0)


class SchemaForMethodField(schema.Schema):
    value = fields.Integer()


class TypedMethodFieldRequestSchema(schema.Schema):
    method_value = fields.Method(None, "load_value")

    @apispec_method_decorator(SchemaForMethodField(many=True))
    def load_value(self, value: List[int]):
        return [random.randint(2**62, 2**63) + _ for _ in value]


class TypedMethodFieldResponseSchema(schema.Schema):
    method_value = fields.Method("dump_value", None)

    @apispec_method_decorator(fields.List(fields.UUID(), allow_none=False, required=True))
    def dump_value(self, obj: dict):
        return [uuid.UUID(int=_) for _ in obj["method_value"]]
