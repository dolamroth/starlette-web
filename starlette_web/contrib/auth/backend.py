import logging
from typing import Tuple

from sqlalchemy import select
from jwt import InvalidTokenError, ExpiredSignatureError

from starlette_web.contrib.auth.models import User, UserSession
from starlette_web.contrib.auth.utils import decode_jwt, TOKEN_TYPE_ACCESS
from starlette_web.common.authorization.backends import BaseAuthenticationBackend
from starlette_web.common.http.exceptions import (
    AuthenticationFailedError,
    AuthenticationRequiredError,
    SignatureExpiredError,
)

logger = logging.getLogger(__name__)


class JWTAuthenticationBackend(BaseAuthenticationBackend):
    """Core of authenticate system, based on JWT auth approach"""

    keyword = "Bearer"
    openapi_spec = {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}
    openapi_name = "JWTAuth"

    async def authenticate(self, **kwargs) -> User:
        request = self.request

        auth_header = request.headers.get("Authorization") or request.headers.get("authorization")
        if not auth_header:
            raise AuthenticationRequiredError("Invalid token header. No credentials provided.")

        auth = auth_header.split()
        if len(auth) != 2:
            logger.warning("Trying to authenticate with header %s", auth_header)
            raise AuthenticationFailedError("Invalid token header. Token should be format as JWT.")

        if auth[0] != self.keyword:
            raise AuthenticationFailedError("Invalid token header. Keyword mismatch.")

        user, _, session_id = await self.authenticate_user(jwt_token=auth[1], **kwargs)

        self.scope["user_session_id"] = session_id
        self.scope["user"] = user
        return user

    @staticmethod
    def _parse_jwt_payload(jwt_token: str, token_type: str) -> dict:
        logger.debug("Logging via JWT auth. Got token: %s", jwt_token)
        try:
            # TODO: class-based JWT decoder
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
        token_type: str = TOKEN_TYPE_ACCESS,
        **kwargs,
    ) -> Tuple[User, dict, str]:
        """Allows to find active user by jwt_token"""
        jwt_payload = self._parse_jwt_payload(jwt_token, token_type)

        user_id = jwt_payload.get("user_id")

        query = select(User).filter(User.id == user_id, User.is_active.is_(True))
        user = (await self.request.state.db_session.execute(query)).scalars().first()

        if not user:
            msg = "Couldn't found active user with id=%s."
            logger.warning(msg, user_id)
            raise AuthenticationFailedError(details=(msg % (user_id,)))

        session_id = jwt_payload.get("session_id")
        if not session_id:
            raise AuthenticationFailedError("Incorrect data in JWT: session_id is missed")

        query = select(UserSession).filter(
            UserSession.public_id == session_id,
            UserSession.is_active.is_(True),
        )
        user_session = (await self.request.state.db_session.execute(query)).scalars().first()
        if not user_session:
            raise AuthenticationFailedError(
                f"Couldn't found active session: {user_id=} | {session_id=}."
            )

        return user, jwt_payload, session_id


class SessionJWTAuthenticationBackend(JWTAuthenticationBackend):
    cookie_name = "session"

    async def authenticate(self, **kwargs) -> User:
        cookie_value = self.request.cookies.get(self.cookie_name)
        if not cookie_value:
            raise AuthenticationRequiredError("Cookie not found or is empty.")

        user, _, session_id = await self.authenticate_user(jwt_token=cookie_value, **kwargs)

        self.scope["user_session_id"] = session_id
        self.scope["user"] = user
        return user
