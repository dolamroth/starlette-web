from sqlalchemy import select, update
from starlette.requests import Request
from starlette.responses import Response
from starlette_admin.auth import AdminUser, AuthProvider
from starlette_admin.exceptions import LoginFailed

from starlette_web.common.http.exceptions import AuthenticationFailedError, PermissionDeniedError
from starlette_web.contrib.auth.backend import SessionJWTAuthenticationBackend
from starlette_web.contrib.auth.views import JWTSessionMixin
from starlette_web.contrib.auth.models import User, UserSession
from starlette_web.contrib.auth.permissions import IsSuperuserPermission
from starlette_web.contrib.auth.utils import TOKEN_TYPE_REFRESH, decode_jwt


class AdminAuthProvider(AuthProvider):
    async def login(
        self,
        username: str,
        password: str,
        remember_me: bool,
        request: Request,
        response: Response,
    ) -> Response:
        query = select(User).filter(User.email == username, User.is_active.is_(True))
        user = (await request.state.session.execute(query)).scalars().first()
        if not user:
            raise LoginFailed("Invalid username or password")

        if not user.verify_password(password):
            raise LoginFailed("Invalid username or password")

        if not user.is_superuser:
            raise LoginFailed(PermissionDeniedError.message)

        token_maker = JWTSessionMixin()
        token_maker.db_session = request.state.session
        token_collection = await token_maker._create_session(user)

        query = update(UserSession)\
            .filter(UserSession.refresh_token == token_collection.refresh_token)\
            .values(is_persistent=remember_me)

        await request.state.session.execute(query)
        await request.state.session.commit()

        request.scope["session"] = {
            "token": token_collection.refresh_token,
            **decode_jwt(token_collection.refresh_token),
        }
        return response

    async def is_authenticated(self, request) -> bool:
        try:
            await SessionJWTAuthenticationBackend(request, request.scope,).authenticate(
                token_type=TOKEN_TYPE_REFRESH,
            )
            return await IsSuperuserPermission().has_permission(request, request.scope)
        except (AuthenticationFailedError, PermissionDeniedError):
            return False

    def get_admin_user(self, request: Request) -> AdminUser:
        if "user" in request.scope:
            username = request.scope["user"].email
        else:
            username = "Anonymous"
        return AdminUser(username=username, photo_url=None)

    async def logout(self, request: Request, response: Response) -> Response:
        request.scope["session"] = {}
        return response
