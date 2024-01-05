import json
import pickle
from typing import Any

from starlette_web.common.utils.serializers import (
    BytesSerializer,
    SerializeError,
    DeserializeError,
)


class MQTTSerializer(BytesSerializer):
    def serialize(self, content: Any) -> Any:
        if isinstance(content, (bytes, bytearray, memoryview)):
            return bytes(content)

        if isinstance(content, str):
            return content.encode()

        try:
            return json.dumps(content).encode()
        except (TypeError, ValueError):
            pass

        try:
            return pickle.dumps(content)
        except pickle.PickleError as exc:
            raise SerializeError from exc

    def deserialize(self, content: Any) -> Any:
        try:
            return json.loads(content)
        except (TypeError, ValueError, json.JSONDecodeError):
            pass

        try:
            return pickle.loads(content)
        except pickle.UnpicklingError:
            pass

        try:
            return content.decode()
        except UnicodeDecodeError as exc:
            raise DeserializeError from exc
