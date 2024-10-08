import base64
import json
import logging
import uuid
from uuid import UUID
from datetime import datetime, timedelta
from typing import Tuple, Optional, Union

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from starlette_web.common.conf import settings
from starlette_web.common.email import send_email, EmailSenderError
from starlette_web.common.http.base_endpoint import BaseHTTPEndpoint
from starlette_web.common.http.exceptions import (
    AuthenticationFailedError,
    InvalidParameterError,
    SendRequestError,
    ConflictError,
    UnprocessableEntityError,
)
from starlette_web.common.utils import get_random_string
from starlette_web.contrib.auth.models import User, UserSession, UserInvite
from starlette_web.contrib.auth.backend import JWTAuthenticationBackend
from starlette_web.contrib.auth.permissions import IsSuperuserPermission
from starlette_web.contrib.auth.utils import (
    encode_jwt,
    TokenCollection,
    TOKEN_TYPE_REFRESH,
    TOKEN_TYPE_RESET_PASSWORD,
)
from starlette_web.contrib.auth.schemas import (
    SignInSchema,
    SignUpSchema,
    JWTResponseSchema,
    RefreshTokenSchema,
    UserResponseSchema,
    ChangePasswordSchema,
    UserInviteRequestSchema,
    UserInviteResponseSchema,
    ResetPasswordRequestSchema,
    ResetPasswordResponseSchema,
)
from starlette_web.contrib.auth.password_validation import validate_password

logger = logging.getLogger(__name__)


# TODO: rewrite as separate manager, not bound to views
class JWTSessionMixin:
    """Allows updating session and prepare usual / refresh JWT tokens"""

    response_schema = JWTResponseSchema
    db_session: AsyncSession = NotImplemented

    @staticmethod
    def _get_tokens(user: User, session_id: Union[str, UUID]) -> TokenCollection:
        token_payload = {"user_id": user.id, "session_id": str(session_id)}
        access_token, access_token_expired_at = encode_jwt(token_payload)
        refresh_token, refresh_token_expired_at = encode_jwt(
            token_payload,
            token_type=TOKEN_TYPE_REFRESH,
        )
        return TokenCollection(
            refresh_token=refresh_token,
            refresh_token_expired_at=refresh_token_expired_at,
            access_token=access_token,
            access_token_expired_at=access_token_expired_at,
        )

    async def _create_session(self, user: User) -> TokenCollection:
        session_id = uuid.uuid4()
        token_collection = self._get_tokens(user, session_id)
        user_session = UserSession(
            user_id=user.id,
            public_id=str(session_id),
            refresh_token=token_collection.refresh_token,
            expired_at=token_collection.refresh_token_expired_at,
        )
        self.db_session.add(user_session)
        await self.db_session.flush()
        return token_collection

    async def _update_session(self, user: User, session_id: Union[str, UUID]) -> TokenCollection:
        query = (
            select(UserSession).filter(UserSession.public_id == str(session_id)).with_for_update()
        )
        user_session = (await self.db_session.execute(query)).scalars().first()

        if user_session is None:
            return await self._create_session(user)

        token_collection = self._get_tokens(user, session_id=session_id)
        user_session.refresh_token = token_collection.refresh_token
        user_session.expired_at = token_collection.refresh_token_expired_at
        user_session.refreshed_at = datetime.utcnow()
        user_session.is_active = True
        await self.db_session.flush()

        return token_collection


class SignInAPIView(JWTSessionMixin, BaseHTTPEndpoint):
    """Allows to Log-In user and update/create his session"""

    request_schema = SignInSchema
    auth_backend = None

    async def post(self, request):
        """
        summary: Sign in
        description: Sign in
        requestBody:
          required: true
          description: Sign in
          content:
            application/json:
              schema: SignInSchema
        responses:
          200:
            description: JsonWebToken
            content:
              application/json:
                schema: JWTResponseSchema
          401:
            description: Authentication failed
            content:
              application/json:
                schema: Error
        tags: ["Authorization"]
        """
        cleaned_data = await self._validate(request)
        user = await self.authenticate(cleaned_data["email"], cleaned_data["password"])
        token_collection = await self._create_session(user)
        return self._response(token_collection)

    async def authenticate(self, email: str, password: str) -> User:
        query = select(User).filter(User.email == email, User.is_active.is_(True))
        user = (await self.db_session.execute(query)).scalars().first()
        if not user:
            logger.info("Not found active user with email [%s]", email)
            raise AuthenticationFailedError(
                details="Not found active user with provided email.",
            )

        if not user.verify_password(password):
            logger.error("Password didn't verify: email: %s", email)
            raise AuthenticationFailedError(
                details="Email or password is invalid.",
            )

        return user


class SignUpAPIView(JWTSessionMixin, BaseHTTPEndpoint):
    """Allows creating new user and create his own session"""

    request_schema = SignUpSchema
    auth_backend = None

    async def post(self, request):
        """
        summary: Sign up
        description: Sign up
        requestBody:
          required: true
          description: Sign up
          content:
            application/json:
              schema: SignUpSchema
        responses:
          200:
            description: JsonWebToken
            content:
              application/json:
                schema: JWTResponseSchema
        tags: ["Authorization"]
        """
        cleaned_data = await self._validate(request)
        user_invite: UserInvite = cleaned_data["user_invite"]

        user = User(
            email=cleaned_data["email"],
            password=User.make_password(cleaned_data["password_1"]),
        )
        self.db_session.add(user)
        await self.db_session.flush()
        await self.db_session.refresh(user)

        user_invite.user_id = user.id
        user_invite.is_applied = True
        await self.db_session.flush()

        token_collection = await self._create_session(user)
        return self._response(token_collection, status_code=status.HTTP_201_CREATED)

    async def _validate(self, request, *_) -> dict:
        cleaned_data = (await super()._validate(request)) or dict()
        email = cleaned_data["email"]

        query = select(User).filter(User.email == email)
        user = (await self.db_session.execute(query)).scalars().first()

        if user is not None:
            raise ConflictError(details=f"User with email '{email}' already exists")

        query = select(UserInvite).filter(
            UserInvite.token == cleaned_data["invite_token"],
            UserInvite.is_applied.is_(False),
            UserInvite.expired_at > datetime.utcnow(),
        )
        user_invite = (await self.db_session.execute(query)).scalars().first()

        if not user_invite:
            details = "Invitation link is expired or unavailable"
            logger.error(
                "Couldn't signup user token: %s | details: %s",
                cleaned_data["invite_token"],
                details,
            )
            raise UnprocessableEntityError(details=details)

        if email != user_invite.email:
            raise InvalidParameterError(message="Email does not match with your invitation.")

        validate_password(cleaned_data["password_1"], User(email=email))

        cleaned_data["user_invite"] = user_invite
        return cleaned_data


class SignOutAPIView(BaseHTTPEndpoint):
    """
    Sign-out consists from 2 operations:
     - remove JWT token on front-end side
     - deactivate current session on BE (this allows to block use regular or refresh token)
    """

    auth_backend = JWTAuthenticationBackend

    async def delete(self, request):
        """
        summary: Sign out
        description: Sign out
        responses:
          200:
            description: Signed out
        tags: ["Authorization"]
        """
        user = request.user
        logger.info("Log out for user %s", user)

        query = select(UserSession).filter(
            UserSession.public_id == self.scope["user_session_id"],
            UserSession.is_active.is_(True),
        )
        user_session = (await self.db_session.execute(query)).scalars().first()
        if user_session:
            logger.info("Session %s exists and active. It will be updated.", user_session)
            user_session.is_active = False
            await self.db_session.flush()

        else:
            logger.info("Not found active sessions for user %s. Skip sign-out.", user)

        return self._response(status_code=status.HTTP_200_OK)


class RefreshTokenAPIView(JWTSessionMixin, BaseHTTPEndpoint):
    """Allows updating tokens (should be called when main token is outdated)"""

    request_schema = RefreshTokenSchema
    auth_backend = None

    async def post(self, request):
        """
        summary: Update refresh token
        description: Update refresh token
        requestBody:
          required: true
          description: Refresh token
          content:
            application/json:
              schema: RefreshTokenSchema
        responses:
          200:
            description: JsonWebToken
            content:
              application/json:
                schema: JWTResponseSchema
          401:
            description: Authentication failed
            content:
              application/json:
                schema: Error
        tags: ["Authorization"]
        """
        user, refresh_token, session_id = await self._validate(request)
        if session_id is None:
            raise AuthenticationFailedError("No session ID in token found")

        query = select(UserSession).filter(
            UserSession.public_id == session_id,
            UserSession.is_active.is_(True),
        )
        user_session = (await self.db_session.execute(query)).scalars().first()

        if not user_session:
            raise AuthenticationFailedError("There is not active session for user.")

        if user_session.refresh_token != refresh_token:
            raise AuthenticationFailedError("Refresh token does not match with user session.")

        token_collection = await self._update_session(user, session_id)
        return self._response(token_collection)

    async def _validate(self, request, *args, **kwargs) -> Tuple[User, str, Optional[str]]:
        cleaned_data = await super()._validate(request)
        refresh_token = cleaned_data["refresh_token"]
        user, jwt_payload, _ = await JWTAuthenticationBackend(
            request,
            self.scope,
        ).authenticate_user(refresh_token, token_type="refresh")
        return user, refresh_token, jwt_payload.get("session_id")


class InviteUserAPIView(BaseHTTPEndpoint):
    """Invite user (by email) to the service"""

    request_schema = UserInviteRequestSchema
    response_schema = UserInviteResponseSchema
    auth_backend = JWTAuthenticationBackend

    async def post(self, request):
        """
        summary: Invite user
        description: Invite user
        requestBody:
          required: true
          description: Invited user's credentials
          content:
            application/json:
              schema: UserInviteRequestSchema
        responses:
          200:
            description: Invited user
            content:
              application/json:
                schema: UserInviteResponseSchema
        tags: ["Authorization"]
        """
        cleaned_data = await self._validate(request)
        email = cleaned_data["email"]
        token = UserInvite.generate_token()
        expired_at = datetime.utcnow() + timedelta(seconds=settings.AUTH_INVITE_LINK_EXPIRES_IN)

        query = select(UserInvite).filter(UserInvite.email == email)
        user_invite = (await self.db_session.execute(query)).scalars().first()

        if user_invite is not None:
            logger.info("INVITE: update for %s (expired %s) token [%s]", email, expired_at, token)
            user_invite.token = token
            user_invite.expired_at = expired_at
            await self.db_session.flush()
            await self.db_session.refresh(user_invite)

        else:
            logger.info("INVITE: create for %s (expired %s) token [%s]", email, expired_at, token)

            user_invite = UserInvite(
                email=email,
                token=token,
                expired_at=expired_at,
                owner_id=request.user.id,
            )
            self.db_session.add(user_invite)
            await self.db_session.flush()
            await self.db_session.refresh(user_invite)

        logger.info("Invite object %r created. Sending message...", user_invite)
        await self._send_email(user_invite)
        return self._response(user_invite, status_code=status.HTTP_201_CREATED)

    @staticmethod
    async def _send_email(user_invite: UserInvite):
        invite_data = {"token": user_invite.token, "email": user_invite.email}
        invite_data = base64.urlsafe_b64encode(json.dumps(invite_data).encode()).decode()
        link = f"{settings.SITE_URL}/sign-up/?i={invite_data}"
        body = (
            f"<p>Hello! :) You have been invited to {settings.SITE_URL}</p>"
            f"<p>Please follow the link </p>"
            f"<p><a href={link}>{link}</a></p>"
        )

        try:
            await send_email(
                recipients_list=[user_invite.email],
                subject=f"Welcome to {settings.SITE_URL}",
                html_content=body.strip(),
            )
        except EmailSenderError as exc:
            raise SendRequestError(**dict(exc))

    async def _validate(self, request, *_) -> dict:
        cleaned_data = (await super()._validate(request)) or dict()

        query = select(User).filter(User.email == cleaned_data["email"])
        user = (await self.db_session.execute(query)).scalars().first()

        if user is not None:
            raise InvalidParameterError(f"User with email=[{user.email}] already exists.")

        return cleaned_data


class ResetPasswordAPIView(BaseHTTPEndpoint):
    """Send link to user's email for resetting his password"""

    request_schema = ResetPasswordRequestSchema
    response_schema = ResetPasswordResponseSchema
    auth_backend = JWTAuthenticationBackend
    permission_classes = [IsSuperuserPermission]

    async def post(self, request):
        """
        summary: Reset password
        description: Reset password
        requestBody:
          required: true
          description: User credentials
          content:
            application/json:
              schema: ResetPasswordRequestSchema
        responses:
          200:
            description: Link to email
            content:
              application/json:
                schema: ResetPasswordResponseSchema
        tags: ["Authorization"]
        """
        user = await self._validate(request)
        token = self._generate_token(user)
        await self._send_email(user, token)
        return self._response({"user_id": user.id, "email": user.email, "token": token})

    async def _validate(self, request, *_) -> User:
        cleaned_data = await super()._validate(request)
        query = select(User).filter(User.email == cleaned_data["email"])
        user = (await self.db_session.execute(query)).scalars().first()
        if not user:
            raise InvalidParameterError(f"User with email=[{cleaned_data['email']}] not found.")

        return user

    @staticmethod
    async def _send_email(user: User, token: str):
        link = f"{settings.SITE_URL}/change-password/?t={token}"
        body = (
            f"<p>You can reset your password for {settings.SITE_URL}</p>"
            f"<p>Please follow the link </p>"
            f"<p><a href={link}>{link}</a></p>"
        )
        try:
            await send_email(
                recipients_list=[user.email],
                subject=f"Welcome back to {settings.SITE_URL}",
                html_content=body.strip(),
            )
        except EmailSenderError as exc:
            raise SendRequestError(**dict(exc))

    @staticmethod
    def _generate_token(user: User) -> str:
        payload = {
            "user_id": user.id,
            "email": user.email,
            "jti": f"token-{uuid.uuid4()}",  # JWT ID
            "slt": get_random_string(length=12),
        }
        token, _ = encode_jwt(
            payload,
            token_type=TOKEN_TYPE_RESET_PASSWORD,
            expires_in=settings.AUTH_RESET_PASSWORD_LINK_EXPIRES_IN,
        )
        return token


class ChangePasswordAPIView(JWTSessionMixin, BaseHTTPEndpoint):
    """Simple API for changing user's password"""

    request_schema = ChangePasswordSchema
    auth_backend = None

    async def post(self, request):
        """
        summary: Change password
        description: Change password
        requestBody:
          required: true
          description: New password confirmation
          content:
            application/json:
              schema: ChangePasswordSchema
        responses:
          200:
            description: New tokens
            content:
              application/json:
                schema: JWTResponseSchema
          401:
            description: Authentication failed
        tags: ["Authorization"]
        """
        cleaned_data = await self._validate(request)
        validate_password(cleaned_data["password_1"], None)

        user, _, _ = await JWTAuthenticationBackend(request, self.scope).authenticate_user(
            jwt_token=cleaned_data["token"],
            token_type=TOKEN_TYPE_RESET_PASSWORD,
        )
        new_password = User.make_password(cleaned_data["password_1"])

        user.password = new_password
        await self.db_session.flush()

        token_collection = await self._create_session(user)
        return self._response(token_collection)


class ProfileApiView(BaseHTTPEndpoint):
    """Simple retrieves profile information (for authenticated user)"""

    response_schema = UserResponseSchema
    auth_backend = JWTAuthenticationBackend

    async def get(self, request):
        """
        summary: Profile info
        description: Profile info
        responses:
          200:
            description: Profile
            content:
              application/json:
                schema: UserResponseSchema
        tags: ["Authorization"]
        """
        return self._response(request.user)
