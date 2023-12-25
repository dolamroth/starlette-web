import copy
import datetime
from functools import cached_property
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
            expires_in=expires_in,
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
            key=self._get_encode_secret_key,
            **self._get_encode_options(**self.init_options, **kwargs),
        )
        return token, _expires_at

    def decode_jwt(self, encoded_jwt: str, **kwargs):
        return jwt.decode(
            encoded_jwt,
            key=self._get_decode_secret_key,
            **self._get_decode_options(**self.init_options, **kwargs),
        )

    @cached_property
    def _get_encode_secret_key(self):
        raise NotImplementedError()

    @cached_property
    def _get_decode_secret_key(self):
        raise NotImplementedError()

    def _get_expires_at(self, expires_in: int = None, **kwargs) -> datetime.datetime:
        return datetime.datetime.utcnow() + datetime.timedelta(seconds=expires_in)

    def _enhance_payload_for_encode(self, payload: dict, **kwargs) -> None:
        pass

    def _get_encode_options(self, **kwargs) -> dict:
        res = {}
        options = {**self.init_options, **kwargs}

        if "algorithm" in options:
            res["algorithm"] = options["algorithm"]

        return res

    def _get_decode_options(self, **kwargs) -> dict:
        res = {}
        options = {**self.init_options, **kwargs}

        if "algorithm" in options:
            res["algorithms"] = [options["algorithm"]]
        elif "algorithms" in options:
            res["algorithms"] = options["algorithms"]

        if "options" in options:
            res["options"] = options["options"]
        else:
            res["options"] = options

        return res
