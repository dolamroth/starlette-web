import datetime
from dataclasses import dataclass

from starlette_web.common.conf import settings
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
    def _get_encode_secret_key(self, **kwargs):
        return str(settings.SECRET_KEY)

    def _get_decode_secret_key(self, **kwargs):
        return str(settings.SECRET_KEY)

    def _get_expires_at(self, expires_in_base: int = None, **kwargs) -> datetime.datetime:
        token_type: str = kwargs.get("token_type", TOKEN_TYPE_ACCESS)

        if token_type == TOKEN_TYPE_REFRESH:
            expires_in = settings.AUTH_JWT_REFRESH_EXPIRES_IN
        else:
            expires_in = expires_in_base or settings.AUTH_JWT_EXPIRES_IN

        return super()._get_expires_at(expires_in_base=expires_in)

    def _enhance_payload_for_encode(self, payload: dict, **kwargs) -> None:
        token_type: str = kwargs.get("token_type", TOKEN_TYPE_ACCESS)
        payload["exp_iso"] = payload["exp"].isoformat()
        payload["token_type"] = token_type

    def _get_encode_options(self, **kwargs) -> dict:
        return {
            "algorithm": settings.AUTH_JWT_ALGORITHM,
        }

    def _get_decode_options(self, **kwargs) -> dict:
        return {
            "algorithms": [settings.AUTH_JWT_ALGORITHM],
        }


jwt_processor = AuthJWTProcessor()
encode_jwt = jwt_processor.encode_jwt
decode_jwt = jwt_processor.decode_jwt
