import base64
import json
import os
import uuid
from datetime import datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from starlette_web.common.conf import settings
from starlette_web.contrib.auth.models import User, UserSession, UserInvite
from starlette_web.contrib.auth.utils import (
    decode_jwt,
    encode_jwt,
    TOKEN_TYPE_RESET_PASSWORD,
    TOKEN_TYPE_REFRESH,
    TOKEN_TYPE_ACCESS,
)
from starlette_web.tests.core.test_base import BaseTestAPIView
from starlette_web.tests.helpers import await_

INVALID_SIGN_IN_DATA = [
    [{"email": "fake-email"}, {"email": "Not a valid email address."}],
    [{"password": ""}, {"password": "Length must be between 2 and 32."}],
    [
        {},
        {
            "email": "Missing data for required field.",
            "password": "Missing data for required field.",
        },
    ],
]

INVALID_SIGN_UP_DATA = [
    [
        {},
        {
            "email": "Missing data for required field.",
            "password_1": "Missing data for required field.",
            "password_2": "Missing data for required field.",
            "invite_token": "Missing data for required field.",
        },
    ],
    [
        {"email": ("user_" * 30 + "@t.com")},
        {"email": "Longer than maximum length 128."},
    ],
    [
        {"email": "fake-email"},
        {"email": "Not a valid email address."},
    ],
    [
        {
            "email": "test@test.com",
            "invite_token": uuid.uuid4().hex,
            "password_1": "Head",
            "password_2": "Foo",
        },
        {"password_1": "Passwords must be equal", "password_2": "Passwords must be equal"},
    ],
    [
        {"invite_token": "token"},
        {"invite_token": "Length must be between 10 and 32."},
    ],
]
INVALID_INVITE_DATA = [
    [{"email": "fake-email"}, {"email": "Not a valid email address."}],
    [{}, {"email": "Missing data for required field."}],
]
INVALID_CHANGE_PASSWORD_DATA = [
    [{"password_1": "123456", "token": "t"}, {"password_2": "Missing data for required field."}],
    [{"password_1": "foo", "password_2": "foo"}, {"token": "Missing data for required field."}],
    [
        {"password_1": "header", "password_2": "footer", "token": "t"},
        {"password_1": "Passwords must be equal", "password_2": "Passwords must be equal"},
    ],
    [
        {"password_1": "header", "password_2": "footer", "token": ""},
        {"token": "Shorter than minimum length 1."},
    ],
]


def assert_tokens(response_data: dict, user: User, session_id: str = None):
    """Allows to check access- and refresh-tokens in the response body"""

    access_token = response_data.get("access_token")
    refresh_token = response_data.get("refresh_token")
    assert access_token, f"No access_token in response: {response_data}"
    assert refresh_token, f"No refresh_token in response: {response_data}"

    decoded_access_token = decode_jwt(access_token)
    access_exp_dt = datetime.fromisoformat(decoded_access_token.pop("exp_iso"))
    assert access_exp_dt > datetime.utcnow()
    assert decoded_access_token.get("user_id") == user.id, decoded_access_token
    assert decoded_access_token.get("token_type") == "access", decoded_access_token

    decoded_refresh_token = decode_jwt(refresh_token)
    refresh_exp_dt = datetime.fromisoformat(decoded_refresh_token.pop("exp_iso"))
    assert refresh_exp_dt > datetime.utcnow()
    assert decoded_refresh_token.get("user_id") == user.id, decoded_refresh_token
    assert decoded_refresh_token.get("token_type") == "refresh", decoded_refresh_token
    assert refresh_exp_dt > access_exp_dt

    if session_id:
        assert decoded_refresh_token.get("session_id") == session_id


class TestAuthMeAPIView(BaseTestAPIView):
    url = "/api/auth/me/"

    def test_get__ok(self, client, user):
        client.login(user)
        response = client.get(self.url)
        response_data = self.assert_ok_response(response)
        assert response_data == {
            "id": user.id,
            "email": user.email,
            "is_active": True,
            "is_superuser": user.is_superuser,
        }


class TestAuthSignInAPIView(BaseTestAPIView):
    url = "/api/auth/sign-in/"
    raw_password = "test-password"
    default_fail_status_code = 401

    @classmethod
    def setup_class(cls):
        cls.encoded_password = User.make_password(cls.raw_password)

    def setup_method(self):
        self.email = f"user_{uuid.uuid4().hex[:10]}@test.com"

    def _create_user(self, db_session, is_active=True):
        self.user = User(
            email=self.email,
            password=self.encoded_password,
            is_active=is_active,
        )
        db_session.add(self.user)
        await_(db_session.commit())
        await_(db_session.refresh(self.user))

    def test_sign_in__ok(self, client, dbs):
        self._create_user(dbs)
        response = client.post(self.url, json={"email": self.email, "password": self.raw_password})
        response_data = self.assert_ok_response(response)
        assert_tokens(response_data, self.user)

    def test_sign_in__check_user_session__ok(self, client, dbs):
        self._create_user(dbs)
        response = client.post(self.url, json={"email": self.email, "password": self.raw_password})
        response_data = self.assert_ok_response(response)

        refresh_token = response_data.get("refresh_token")
        decoded_refresh_token = decode_jwt(refresh_token)
        refresh_exp_dt = datetime.fromisoformat(decoded_refresh_token.pop("exp_iso"))

        query = select(UserSession).filter(UserSession.user_id == self.user.id)
        user_session: UserSession = await_(dbs.execute(query)).scalars().first()

        assert user_session.refresh_token == refresh_token
        assert user_session.is_active is True
        assert user_session.expired_at == refresh_exp_dt
        assert user_session.refreshed_at is not None
        assert decoded_refresh_token.get("session_id") == user_session.public_id

    def test_sign_in__create_new_user_session__ok(self, client, dbs):
        self._create_user(dbs)
        old_expired_at = datetime.now() + timedelta(seconds=1)

        old_user_session = UserSession(
            is_active=True,
            user_id=self.user.id,
            public_id=str(uuid.uuid4()),
            refresh_token="refresh_token",
            expired_at=old_expired_at,
        )
        dbs.add(old_user_session)
        await_(dbs.flush())
        await_(dbs.refresh(old_user_session))

        response = client.post(self.url, json={"email": self.email, "password": self.raw_password})
        response_data = self.assert_ok_response(response)
        refresh_token = response_data.get("refresh_token")

        query = select(UserSession).filter(UserSession.user_id == self.user.id)
        user_sessions: list[UserSession] = await_(dbs.execute(query)).scalars().all()

        assert len(user_sessions) == 2
        old_session, new_session = user_sessions

        assert old_session.id == old_user_session.id
        assert old_session.is_active is True
        assert old_session.expired_at == old_expired_at
        assert old_session.refreshed_at == old_user_session.refreshed_at

        assert new_session.refresh_token == refresh_token
        assert new_session.is_active is True
        assert old_session.refreshed_at is not None

    def test_sign_in__password_mismatch__fail(self, client, dbs):
        self._create_user(dbs)
        response = client.post(self.url, json={"email": self.email, "password": "fake-password"})
        response_data = self.assert_fail_response(response)
        assert response_data == {
            "error": "Authentication credentials are invalid.",
            "details": "Email or password is invalid.",
        }

    def test_sign_in__user_not_found__fail(self, client):
        response = client.post(self.url, json={"email": "fake@t.ru", "password": self.raw_password})
        response_data = self.assert_fail_response(response)
        assert response_data == {
            "error": "Authentication credentials are invalid.",
            "details": "Not found active user with provided email.",
        }

    @pytest.mark.parametrize("invalid_data, error_details", INVALID_SIGN_IN_DATA)
    def test_sign_in__invalid_request__fail(self, client, invalid_data: dict, error_details: dict):
        self.assert_bad_request(client.post(self.url, json=invalid_data), error_details)

    def test_sign_in__user_inactive__fail(self, client, dbs):
        self._create_user(dbs, is_active=False)
        response = client.post(self.url, json={"email": self.email, "password": self.raw_password})
        response_data = self.assert_fail_response(response)
        assert response_data == {
            "error": "Authentication credentials are invalid.",
            "details": "Not found active user with provided email.",
        }


class TestAuthSignUPAPIView(BaseTestAPIView):
    url = "/api/auth/sign-up/"
    default_fail_status_code = 400

    @staticmethod
    def _sign_up_data(user_invite: UserInvite):
        return {
            "email": user_invite.email,
            "invite_token": user_invite.token,
            "password_1": "test-password",
            "password_2": "test-password",
        }

    def test_sign_up__ok(self, client, user_invite, dbs):
        request_data = self._sign_up_data(user_invite)
        response = client.post(self.url, json=request_data)
        response_data = self.assert_ok_response(response, status_code=201)

        query = select(User).filter(User.email == request_data["email"])
        user = await_(dbs.execute(query)).scalars().first()

        assert user is not None, f"User wasn't created with {request_data=}"
        assert_tokens(response_data, user)

        await_(dbs.refresh(user_invite))
        assert user_invite.user_id == user.id
        assert user_invite.is_applied

    @pytest.mark.parametrize("invalid_data, error_details", INVALID_SIGN_UP_DATA)
    def test_sign_up__invalid_request__fail(self, client, invalid_data: dict, error_details: dict):
        self.assert_bad_request(client.post(self.url, json=invalid_data), error_details)

    def test_sign_up__user_already_exists__fail(self, client, user_invite, dbs):
        request_data = self._sign_up_data(user_invite)
        user_email = request_data["email"]

        user = User(
            email=user_email,
            password=User.make_password("pass"),
        )
        dbs.add(user)
        await_(dbs.commit())

        response = client.post(self.url, json=request_data)
        response_data = self.assert_fail_response(response, status_code=409)
        assert response_data == {
            "error": "Request conflicts with current state of server.",
            "details": f"User with email '{user_email}' already exists",
        }

    @pytest.mark.parametrize(
        "token_update_data",
        [
            {"token": f"outdated-token-{uuid.uuid4().hex[:10]}"},
            {"expired_at": datetime.utcnow() - timedelta(hours=1)},
            {"is_applied": True},
        ],
    )
    def test_sign_up__token_problems__fail(self, client, user_invite, token_update_data, dbs):
        request_data = self._sign_up_data(user_invite)

        for key, value in token_update_data.items():
            setattr(user_invite, key, value)

        await_(dbs.commit())

        response = client.post(self.url, json=request_data)
        response_data = self.assert_fail_response(response, status_code=422)
        assert response_data == {
            "error": "Could not process request due to logical errors in data.",
            "details": "Invitation link is expired or unavailable",
        }

    def test_sign_up__email_mismatch_with_token__fail(self, client, user_invite):
        request_data = self._sign_up_data(user_invite)
        request_data["email"] = f"another.email{uuid.uuid4().hex[:10]}@test.com"
        response = client.post(self.url, json=request_data)
        response_data = self.assert_fail_response(response)
        assert response_data["error"] == "Email does not match with your invitation."


class TestSignOutAPIView(BaseTestAPIView):
    url = "/api/auth/sign-out/"

    def test_sign_out__ok(self, client, user, dbs):
        user_session = client.login(user)
        response = client.delete(self.url)
        assert response.status_code == 200

        query = select(UserSession).filter(UserSession.id == user_session.id)
        user_session = await_(dbs.execute(query)).scalars().first()
        assert user_session.is_active is False

    def test_sign_out__user_session_not_found__ok(self, client, user):
        client.login(user)
        response = client.delete(self.url)
        assert response.status_code == 200


class TestUserInviteApiView(BaseTestAPIView):
    url = "/api/auth/invite-user/"
    default_fail_status_code = 400

    def setup_method(self):
        self.email = f"user_{uuid.uuid4().hex[:10]}@test.com"

    def test_invite__ok(self, client, user, mocked_auth_send, dbs):
        client.login(user)
        response = client.post(self.url, json={"email": self.email})
        response_data = self.assert_ok_response(response, status_code=201)

        query = select(UserInvite).filter(UserInvite.email == self.email)
        user_invite: UserInvite = await_(dbs.execute(query)).scalars().first()
        assert user_invite is not None
        assert response_data == {
            "id": user_invite.id,
            "token": user_invite.token,
            "email": user_invite.email,
            "owner_id": user.id,
            "created_at": user_invite.created_at.isoformat(),
            "expired_at": user_invite.expired_at.isoformat(),
        }
        invite_data = {
            "token": user_invite.token,
            "email": user_invite.email,
        }
        invite_data = base64.urlsafe_b64encode(json.dumps(invite_data).encode()).decode()
        link = f"{settings.SITE_URL}/sign-up/?i={invite_data}"
        expected_body = (
            f"<p>Hello! :) You have been invited to {settings.SITE_URL}</p>"
            f"<p>Please follow the link </p>"
            f"<p><a href={link}>{link}</a></p>"
        )
        mocked_auth_send.assert_awaited_once_with(
            recipients_list=[self.email],
            subject=f"Welcome to {settings.SITE_URL}",
            html_content=expected_body,
        )

    @pytest.mark.parametrize("invalid_data, error_details", INVALID_INVITE_DATA)
    def test_invalid_request__fail(self, client, user, invalid_data: dict, error_details: dict):
        client.login(user)
        self.assert_bad_request(client.post(self.url, json=invalid_data), error_details)

    def test_invite__unauth__fail(self, client):
        client.logout()
        self.assert_unauth(client.post(self.url, json={"email": self.email}))

    def test_invite__user_already_exists__fail(self, client, user):
        client.login(user)
        response = client.post(self.url, json={"email": user.email})

        response_data = self.assert_fail_response(response)
        assert response_data == {
            "error": "Requested data is not valid.",
            "details": f"User with email=[{user.email}] already exists.",
        }

    # TODO: test
    def _test_invite__user_already_invited__update_invite__ok(
        self, client, user, mocked_auth_send, db_session
    ):
        old_token = UserInvite.generate_token()
        old_expired_at = datetime.utcnow()
        user_invite = UserInvite(
            email=self.email,
            token=old_token,
            expired_at=old_expired_at,
            owner_id=user.id,
        )
        db_session.add(user_invite)
        await_(db_session.flush())
        await_(db_session.refresh(user_invite))

        client.login(user)
        client.post(self.url, json={"email": self.email})

        query = select(UserInvite).filter(UserInvite.email == self.email)
        updated_user_invite: UserInvite = await_(db_session.execute(query)).scalars().first()

        assert updated_user_invite is not None
        assert updated_user_invite.id == user_invite.id
        assert updated_user_invite.token != user_invite.token
        assert updated_user_invite.expired_at != user_invite.expired_at
        assert mocked_auth_send.assert_awaited_once


class TestResetPasswordAPIView(BaseTestAPIView):
    url = "/api/auth/reset-password/"

    def setup_method(self):
        self.email = f"user_{uuid.uuid4().hex[:10]}@test.com"

    def test_reset_password__ok(self, client, user, mocked_auth_send, dbs):
        request_user = user
        request_user.is_superuser = True
        target_user = User(
            email=self.email,
            password=User.make_password("pass"),
        )
        dbs.add(target_user)
        await_(dbs.commit())
        await_(dbs.refresh(target_user))

        client.login(user)
        response = client.post(self.url, json={"email": target_user.email})
        response_data = self.assert_ok_response(response)
        token = response_data.get("token")

        assert response_data["user_id"] == target_user.id
        assert token is not None, response_data
        assert decode_jwt(response_data["token"])["user_id"] == target_user.id

        link = f"{settings.SITE_URL}/change-password/?t={token}"
        expected_body = (
            f"<p>You can reset your password for {settings.SITE_URL}</p>"
            f"<p>Please follow the link </p>"
            f"<p><a href={link}>{link}</a></p>"
        )
        mocked_auth_send.assert_awaited_once_with(
            recipients_list=[target_user.email],
            subject=f"Welcome back to {settings.SITE_URL}",
            html_content=expected_body,
        )

    def test_reset_password__unauth__fail(self, client):
        client.logout()
        self.assert_unauth(client.post(self.url, json={"email": self.email}))

    def test_reset_password__user_not_found__fail(self, client, user, mocked_auth_send, dbs):
        request_user = user
        request_user.is_superuser = True
        await_(dbs.commit())
        await_(dbs.refresh(request_user))

        client.login(request_user)
        response = client.post(self.url, json={"email": "fake-email@test.com"})
        response_data = self.assert_fail_response(
            response,
            status_code=400,
        )
        assert response_data == {
            "error": "Requested data is not valid.",
            "details": "User with email=[fake-email@test.com] not found.",
        }

    def test_reset_password__user_is_not_superuser__fail(self, client, user):
        client.login(user)
        response = client.post(self.url, json={"email": user.email})
        response_data = self.assert_fail_response(
            response,
            status_code=403,
        )
        assert response_data == {
            "error": "You do not have permission to perform this action.",
            "details": "You don't have an admin privileges.",
        }


class TestChangePasswordAPIView(BaseTestAPIView):
    url = "/api/auth/change-password/"
    new_password = "new123456"

    def _assert_fail_response(self, client, token: str) -> dict:
        request_data = {
            "token": token,
            "password_1": self.new_password,
            "password_2": self.new_password,
        }
        client.logout()
        response = client.post(self.url, json=request_data)
        assert response.status_code == 401
        return response.json()

    def test_change_password__ok(self, client, user, user_session, dbs):
        token, _ = encode_jwt(
            {"user_id": user.id, "session_id": user_session.public_id},
            token_type=TOKEN_TYPE_RESET_PASSWORD,
        )
        request_data = {
            "token": token,
            "password_1": self.new_password,
            "password_2": self.new_password,
        }
        client.logout()
        response = client.post(self.url, json=request_data)
        response_data = self.assert_ok_response(response)
        assert_tokens(response_data, user)

        await_(dbs.refresh(user))
        assert user.verify_password(self.new_password)

    @pytest.mark.parametrize("invalid_data, error_details", INVALID_CHANGE_PASSWORD_DATA)
    def test_invalid_request__fail(self, client, invalid_data: dict, error_details: dict):
        client.logout()
        self.assert_bad_request(client.post(self.url, json=invalid_data), error_details)

    def test__token_expired__fail(self, client, user):
        token, _ = encode_jwt({"user_id": user.id}, expires_in=-10)
        response_data = self._assert_fail_response(client, token)
        self.assert_auth_invalid(
            response_data,
            "JWT signature has been expired for token",
            message="Authentication credentials have expired.",
        )

    def test__token_invalid_type__fail(self, client, user):
        token, _ = encode_jwt({"user_id": user.id}, token_type=TOKEN_TYPE_REFRESH)
        response_data = self._assert_fail_response(client, token)
        self.assert_auth_invalid(
            response_data, "Token type 'reset_password' expected, got 'refresh' instead."
        )

    def test_token_invalid__fail(self, client, user):
        response_data = self._assert_fail_response(client, "fake-jwt")
        self.assert_auth_invalid(response_data, "Token could not be decoded: Not enough segments")

    def test_user_inactive__fail(self, client, user, dbs):
        user.is_active = False
        await_(dbs.commit())
        await_(dbs.refresh(user))

        token, _ = encode_jwt({"user_id": user.id}, token_type=TOKEN_TYPE_RESET_PASSWORD)
        response_data = self._assert_fail_response(client, token)
        self.assert_auth_invalid(response_data, f"Couldn't found active user with id={user.id}.")

    def test_user_does_not_exist__fail(self, client, user):
        user_id = 0
        token, _ = encode_jwt({"user_id": user_id}, token_type=TOKEN_TYPE_RESET_PASSWORD)
        response_data = self._assert_fail_response(client, token)
        self.assert_auth_invalid(response_data, f"Couldn't found active user with id={user_id}.")


class TestRefreshTokenAPIView(BaseTestAPIView):
    url = "/api/auth/refresh-token/"

    INVALID_REFRESH_TOKEN_DATA = [
        [{}, {"refresh_token": "Missing data for required field."}],
        [{"refresh_token": ""}, {"refresh_token": "Length must be between 10 and 512."}],
    ]

    @staticmethod
    def _prepare_token(
        db_session: AsyncSession, user: User, is_active=True, refresh=True
    ) -> UserSession:
        token_type = TOKEN_TYPE_REFRESH if refresh else TOKEN_TYPE_ACCESS
        session_id = str(uuid.uuid4())
        refresh_token, _ = encode_jwt(
            {"user_id": user.id, "session_id": session_id}, token_type=token_type
        )
        user_session = UserSession(
            user_id=user.id,
            is_active=is_active,
            public_id=session_id,
            refresh_token=refresh_token,
            expired_at=datetime.utcnow(),
        )
        db_session.add(user_session)
        await_(db_session.commit())
        await_(db_session.refresh(user_session))

        return user_session

    def test_refresh_token__ok(self, client, user, dbs):
        user_session = self._prepare_token(dbs, user)
        client.logout()
        response = client.post(self.url, json={"refresh_token": user_session.refresh_token})
        response_data = self.assert_ok_response(response)
        assert_tokens(response_data, user)

    def test_refresh_token__several_sessions_for_user__ok(self, client, user, dbs):
        user_session_1 = self._prepare_token(dbs, user)
        user_session_2 = self._prepare_token(dbs, user)
        client.logout()
        response = client.post(self.url, json={"refresh_token": user_session_2.refresh_token})
        response_data = self.assert_ok_response(response)
        assert_tokens(response_data, user, session_id=user_session_2.public_id)

        query_1 = select(UserSession).filter(UserSession.id == user_session_1.id)
        upd_user_session_1: UserSession = await_(dbs.execute(query_1)).scalars().first()

        query_2 = select(UserSession).filter(UserSession.id == user_session_2.id)
        upd_user_session_2: UserSession = await_(dbs.execute(query_2)).scalars().first()

        assert user_session_1.refreshed_at == upd_user_session_1.refreshed_at
        assert user_session_1.refresh_token == upd_user_session_1.refresh_token

        if os.name == "nt":
            # Windows has less time ticks, than Linux,
            # so sometimes these 2 times are equal up to milliseconds
            assert user_session_1.refreshed_at <= upd_user_session_2.refreshed_at
        else:
            assert user_session_1.refreshed_at < upd_user_session_2.refreshed_at

    def test_refresh_token__user_inactive__fail(self, client, user, dbs):
        user_session = self._prepare_token(dbs, user)

        user.is_active = False
        await_(dbs.commit())
        await_(dbs.refresh(user))

        response = client.post(self.url, json={"refresh_token": user_session.refresh_token})
        self.assert_auth_invalid(response, f"Couldn't found active user with id={user.id}.")

    def test_refresh_token__session_inactive__fail(self, client, user, dbs):
        session = self._prepare_token(dbs, user, is_active=False)
        response = client.post(self.url, json={"refresh_token": session.refresh_token})
        expected_msg = (
            f"Couldn't found active session: user_id={user.id} | session_id='{session.public_id}'."
        )
        self.assert_auth_invalid(response, expected_msg)

    @pytest.mark.parametrize("token_type", [TOKEN_TYPE_ACCESS, TOKEN_TYPE_RESET_PASSWORD])
    def test_refresh_token__token_not_refresh__fail(self, client, user, token_type):
        refresh_token, _ = encode_jwt({"user_id": user.id}, token_type=token_type)
        response = client.post(self.url, json={"refresh_token": refresh_token})
        response_data = self.assert_fail_response(response, status_code=401)
        assert response_data == {
            "error": "Authentication credentials are invalid.",
            "details": f"Token type 'refresh' expected, got '{token_type}' instead.",
        }

    def test_refresh_token__token_mismatch__fail(self, client, user, dbs):
        user_session = self._prepare_token(dbs, user, is_active=True)
        refresh_token = user_session.refresh_token

        user_session.refresh_token = "fake-token"
        await_(dbs.commit())

        response = client.post(self.url, json={"refresh_token": refresh_token})
        self.assert_auth_invalid(
            response,
            "Refresh token does not match with user session.",
        )

    def test_refresh_token__fake_jwt__fail(self, client, user):
        response = client.post(self.url, json={"refresh_token": "fake-jwt-token"})
        self.assert_auth_invalid(response, "Token could not be decoded: Not enough segments")

    @pytest.mark.parametrize("invalid_data, error_details", INVALID_REFRESH_TOKEN_DATA)
    def test_invalid_request__fail(self, client, invalid_data: dict, error_details: dict):
        client.logout()
        self.assert_bad_request(client.post(self.url, json=invalid_data), error_details)
