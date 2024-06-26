import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from starlette_web.common.http.exceptions import (
    AuthenticationRequiredError,
    AuthenticationFailedError,
    PermissionDeniedError,
)
from starlette_web.contrib.auth.backend import JWTAuthenticationBackend
from starlette_web.contrib.auth.models import User, UserSession
from starlette_web.contrib.auth.permissions import IsSuperuserPermission
from starlette_web.contrib.auth.utils import (
    encode_jwt,
    TOKEN_TYPE_RESET_PASSWORD,
    TOKEN_TYPE_REFRESH,
)
from starlette_web.tests.helpers import await_


class TestBackendAuth:
    @staticmethod
    def _prepare_request(db_session: AsyncSession, user: User, user_session: UserSession):
        jwt, _ = encode_jwt({"user_id": user.id, "session_id": user_session.public_id})
        scope = {"type": "http", "headers": [(b"authorization", f"Bearer {jwt}".encode("latin-1"))]}
        request = Request(scope)
        request.state.db_session = db_session
        return request, scope

    def test_check_auth__ok(self, client, user, user_session, dbs):
        request, scope = self._prepare_request(dbs, user, user_session)
        authenticated_user = await_(JWTAuthenticationBackend(request, scope).authenticate())
        assert authenticated_user.id == user.id

    @pytest.mark.parametrize(
        "auth_header, auth_exception, err_details",
        [
            (
                (b"auth", "JWT"),
                AuthenticationRequiredError,
                "Invalid token header. No credentials provided.",
            ),
            (
                (b"authorization", b"JWT"),
                AuthenticationFailedError,
                "Invalid token header. Token should be format as JWT.",
            ),
            (
                (b"authorization", b"FakeKeyword JWT"),
                AuthenticationFailedError,
                "Invalid token header. Keyword mismatch.",
            ),
            (
                (b"authorization", b"Bearer fake-jwt-token"),
                AuthenticationFailedError,
                "Token could not be decoded: Not enough segments",
            ),
        ],
    )
    def test_invalid_token__fail(self, client, user, auth_header, auth_exception, err_details, dbs):
        request = Request(scope={"type": "http", "headers": [auth_header]})
        scope = {"type": "http"}
        request.state.db_session = dbs
        with pytest.raises(auth_exception) as err:
            await_(JWTAuthenticationBackend(request, scope).authenticate())

        assert err.value.details == err_details

    def test_check_auth__user_not_active__fail(self, client, user, user_session, dbs):
        user.is_active = False
        await_(dbs.commit())
        await_(dbs.refresh(user))

        request, scope = self._prepare_request(dbs, user, user_session)
        with pytest.raises(AuthenticationFailedError) as err:
            await_(JWTAuthenticationBackend(request, scope).authenticate())

        assert err.value.details == f"Couldn't found active user with id={user.id}."

    def test_check_auth__session_not_active__fail(self, client, user, user_session, dbs):
        user_session.is_active = False
        await_(dbs.commit())
        await_(dbs.refresh(user_session))

        request, scope = self._prepare_request(dbs, user, user_session)
        with pytest.raises(AuthenticationFailedError) as err:
            await_(JWTAuthenticationBackend(request, scope).authenticate())

        assert err.value.details == (
            f"Couldn't found active session: user_id={user.id} | "
            f"session_id='{user_session.public_id}'."
        )

    @pytest.mark.parametrize("token_type", [TOKEN_TYPE_REFRESH, TOKEN_TYPE_RESET_PASSWORD])
    def test_check_auth__token_t_mismatch__fail(self, client, user, user_session, token_type, dbs):
        user_session.is_active = False
        await_(dbs.commit())
        await_(dbs.refresh(user_session))

        token, _ = encode_jwt({"user_id": user.id}, token_type=token_type)
        request, scope = self._prepare_request(dbs, user, user_session)
        with pytest.raises(AuthenticationFailedError) as err:
            await_(
                JWTAuthenticationBackend(request, scope).authenticate_user(
                    token, token_type="access"
                )
            )

        assert err.value.details == f"Token type 'access' expected, got '{token_type}' instead."

    def test_check_auth__admin_required__ok(self, client, user, user_session, dbs):
        user.is_superuser = True
        await_(dbs.commit())
        await_(dbs.refresh(user))

        request, scope = self._prepare_request(dbs, user, user_session)
        authenticated_user = await_(JWTAuthenticationBackend(request, scope).authenticate())
        assert authenticated_user.id == user.id

        is_admin = await_(IsSuperuserPermission().has_permission(request, scope))
        assert is_admin

    def test_check_auth__admin_required__not_superuser__fail(self, client, user, user_session, dbs):
        user.is_superuser = False
        await_(dbs.commit())
        await_(dbs.refresh(user))

        request, scope = self._prepare_request(dbs, user, user_session)
        with pytest.raises(PermissionDeniedError) as err:
            await_(JWTAuthenticationBackend(request, scope).authenticate())
            await_(IsSuperuserPermission().has_permission(request, scope))

        assert err.value.details == "You don't have an admin privileges."
