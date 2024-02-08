import copy
import datetime
from functools import cached_property
from typing import Tuple

import jwt

from starlette_web.common.utils.inspect import get_available_options


class JWTProcessor:
    def __init__(self, **kwargs):
        self.init_options = kwargs

    def encode_jwt(
        self,
        payload: dict,
        expires_in: int = None,
        **kwargs,
    ) -> Tuple[str, datetime.datetime]:
        _options = {**self.init_options}
        _options.update(kwargs)

        _expires_at = self._get_expires_at(
            expires_in=expires_in,
            **_options,
        )
        _payload = copy.deepcopy(payload)
        _payload["exp"] = _expires_at
        self._enhance_payload_for_encode(
            _payload,
            **_options,
        )

        token = jwt.encode(
            payload=_payload,
            key=self._get_encode_secret_key,
            **self._get_encode_options(**_options),
        )
        return token, _expires_at

    def decode_jwt(self, encoded_jwt: str, **kwargs):
        _options = {**self.init_options}
        _options.update(kwargs)

        return jwt.decode(
            encoded_jwt,
            key=self._get_decode_secret_key,
            **self._get_decode_options(**_options),
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

        for _option in get_available_options(jwt.encode):
            if _option in options:
                res[_option] = options[_option]

        return res

    def _get_decode_options(self, **kwargs) -> dict:
        res = {}
        options = {**self.init_options, **kwargs}

        for _option in get_available_options(jwt.decode):
            if _option in options:
                res[_option] = options[_option]

        if "algorithm" in options and not res.get("algorithms"):
            res["algorithms"] = [options["algorithm"]]

        if "options" not in res:
            res["options"] = options

        return res
