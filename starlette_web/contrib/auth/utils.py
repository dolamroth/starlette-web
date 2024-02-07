import datetime
from dataclasses import dataclass
from functools import cached_property

from starlette_web.common.conf import settings
from starlette_web.common.utils.json import StarletteJSONEncoder
from starlette_web.contrib.auth.jwt_utils import JWTProcessor


TOKEN_TYPE_ACCESS = "access"
TOKEN_TYPE_REFRESH = "refresh"
TOKEN_TYPE_RESET_PASSWORD = "reset_password"


@dataclass
class TokenCollection:
    refresh_token: str
    refresh_token_expired_at: datetime.datetime
    access_token: str
    access_token_expired_at: datetime.datetime


class AuthJWTProcessor(JWTProcessor):
    @cached_property
    def _get_encode_secret_key(self):
        return str(settings.SECRET_KEY)

    @cached_property
    def _get_decode_secret_key(self):
        return str(settings.SECRET_KEY)

    def _get_expires_at(self, expires_in: int = None, **kwargs) -> datetime.datetime:
        token_type: str = kwargs.get("token_type", TOKEN_TYPE_ACCESS)

        if token_type == TOKEN_TYPE_REFRESH:
            expires_in = settings.AUTH_JWT_REFRESH_EXPIRES_IN
        else:
            expires_in = expires_in or settings.AUTH_JWT_EXPIRES_IN

        return super()._get_expires_at(expires_in=expires_in)

    def _enhance_payload_for_encode(self, payload: dict, **kwargs) -> None:
        token_type: str = kwargs.get("token_type", TOKEN_TYPE_ACCESS)
        payload["exp_iso"] = payload["exp"].isoformat()
        payload["token_type"] = token_type


jwt_processor = AuthJWTProcessor(
    algorithm=settings.AUTH_JWT_ALGORITHM,
    verify_signature=True,
    json_encoder=StarletteJSONEncoder,
)
encode_jwt = jwt_processor.encode_jwt
decode_jwt = jwt_processor.decode_jwt
