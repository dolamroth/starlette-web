import logging
from typing import Tuple

from jwt import InvalidTokenError, ExpiredSignatureError

from starlette_web.common.authorization.base_user import BaseUserMixin
from starlette_web.contrib.auth.utils import decode_jwt
from starlette_web.common.authorization.backends import BaseAuthenticationBackend
from starlette_web.common.http.exceptions import (
    AuthenticationFailedError,
    AuthenticationRequiredError,
    SignatureExpiredError,
)

logger = logging.getLogger("starlette_web.common.authorization")


class JWTAuthenticationBackend(BaseAuthenticationBackend):
    """Core of authenticate system, based on JWT auth approach"""

    keyword = "Bearer"
    openapi_spec = {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}
    openapi_name = "JWTAuth"
    requires_database = False

    async def authenticate(self, **kwargs) -> BaseUserMixin:
        auth_header = self._get_auth_header()
        auth = self._parse_auth_header(auth_header)

        user, _, session_id = await self.authenticate_user(jwt_token=auth, **kwargs)
        self.scope["user"] = user
        self.scope["user_session_id"] = session_id
        return user

    def _get_auth_header(self):
        # Note: JavaScript browser API does not allow sending headers when initializing WS connection.
        # You may want to use Sec-WebSocket-Protocol header instead.
        auth_header = self.request.headers.get("Authorization") \
                      or self.request.headers.get("authorization")
        if not auth_header:
            raise AuthenticationRequiredError("Invalid token header. No credentials provided.")

        return auth_header

    def _parse_auth_header(self, auth_header) -> str:
        auth = auth_header.split()
        if len(auth) != 2:
            logger.warning("Trying to authenticate with header %s", auth_header)
            raise AuthenticationFailedError("Invalid token header. Token should be format as JWT.")

        if auth[0] != self.keyword:
            raise AuthenticationFailedError("Invalid token header. Keyword mismatch.")

        return auth[1]

    @staticmethod
    def _parse_jwt_payload(jwt_token: str, token_type: str) -> dict:
        logger.debug("Logging via JWT auth. Got token: %s", jwt_token)
        try:
            jwt_payload = decode_jwt(jwt_token)
        except ExpiredSignatureError:
            logger.debug("JWT signature has been expired for token %s", jwt_token)
            raise SignatureExpiredError("JWT signature has been expired for token")
        except InvalidTokenError as error:
            msg = "Token could not be decoded: %s"
            logger.exception(msg, error)
            raise AuthenticationFailedError(msg % (error,))

        if jwt_payload["token_type"] != token_type:
            raise AuthenticationFailedError(
                f"Token type '{token_type}' expected, got '{jwt_payload['token_type']}' instead."
            )

        return jwt_payload

    async def authenticate_user(
        self,
        jwt_token: str,
        **kwargs,
    ) -> Tuple[BaseUserMixin, dict, str]:
        raise NotImplementedError


class SessionJWTAuthenticationBackend(JWTAuthenticationBackend):
    cookie_name = "session"

    async def authenticate(self, **kwargs) -> BaseUserMixin:
        cookie_value = self.request.cookies.get(self.cookie_name)
        if not cookie_value:
            raise AuthenticationRequiredError("Cookie not found or is empty.")

        user, _, session_id = await self.authenticate_user(jwt_token=cookie_value, **kwargs)
        self.scope["user"] = user
        self.scope["user_session_id"] = session_id
        return user
