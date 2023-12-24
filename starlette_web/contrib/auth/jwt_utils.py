import copy
import datetime
from typing import Tuple

import jwt


class JWTProcessor:
    def __init__(self, **kwargs):
        self.init_options = kwargs

    def encode_jwt(
        self,
        payload: dict,
        expires_in: int = None,
        **kwargs,
    ) -> Tuple[str, datetime.datetime]:
        _expires_at = self._get_expires_at(
            expires_in_base=expires_in,
            **self.init_options,
            **kwargs,
        )
        _payload = copy.deepcopy(payload)
        _payload["exp"] = _expires_at
        self._enhance_payload_for_encode(
            _payload,
            **self.init_options,
            **kwargs,
        )

        token = jwt.encode(
            payload=_payload,
            key=self._get_encode_secret_key(**self.init_options, **kwargs),
            **self._get_encode_options(**self.init_options, **kwargs),
        )
        return token, _expires_at

    def decode_jwt(self, encoded_jwt: str, **kwargs):
        return jwt.decode(
            encoded_jwt,
            key=self._get_decode_secret_key(**self.init_options, **kwargs),
            **self._get_decode_options(**self.init_options, **kwargs),
        )

    def _get_encode_secret_key(self, **kwargs):
        raise NotImplementedError()

    def _get_decode_secret_key(self, **kwargs):
        raise NotImplementedError()

    def _get_expires_at(self, expires_in_base: int = None, **kwargs) -> datetime.datetime:
        return datetime.datetime.utcnow() + datetime.timedelta(seconds=expires_in_base)

    def _enhance_payload_for_encode(self, payload: dict, **kwargs) -> None:
        pass

    def _get_encode_options(self, **kwargs) -> dict:
        return {}

    def _get_decode_options(self, **kwargs) -> dict:
        return {}
