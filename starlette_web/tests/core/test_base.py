import json
from typing import Union, Optional

from httpx import Response
from starlette.testclient import TestClient

from starlette_web.common.database.model_base import ModelBase
from starlette_web.contrib.auth.views import JWTSessionMixin
from starlette_web.contrib.auth.models import UserSession


class BaseTestCase:
    @staticmethod
    def assert_called_with(mock_callable, *args, **kwargs):
        """Check mock object (callable) on call action with provided `args`, `kwargs`"""

        assert mock_callable.called
        mock_call_args = mock_callable.call_args_list[-1]
        if args:
            assert mock_call_args.args == args
        for key, value in kwargs.items():
            assert key in mock_call_args.kwargs, mock_call_args.kwargs
            assert mock_call_args.kwargs[key] == value


class BaseTestAPIView(BaseTestCase):
    url: str = NotImplemented
    default_fail_status_code = 500

    @staticmethod
    def assert_ok_response(response: Response, status_code: int = 200) -> Union[dict, list]:
        assert response.status_code == status_code

        try:
            response_data = response.json()
        except Exception:
            raise AssertionError(response.text)

        assert "error" not in response_data, response_data
        return response_data

    def assert_fail_response(
        self,
        response: Response,
        status_code: int = None,
    ) -> Union[dict, list]:
        response_data = response.json()
        assert response.status_code == (status_code or self.default_fail_status_code)
        assert "error" in response_data, response_data
        assert "details" in response_data, response_data
        return response_data

    @staticmethod
    def assert_bad_request(response: Response, error_details: dict):
        response_data = response.json()
        assert response.status_code == 400
        assert "error" in response_data, response_data
        assert "details" in response_data, response_data
        assert response_data["error"] in "Requested data is not valid."

        for error_field, error_value in error_details.items():
            assert error_field in response_data["details"]
            assert error_value in response_data["details"][error_field]

    @staticmethod
    def assert_not_found(response: Response, instance: ModelBase):
        assert response.status_code == 404
        response_data = response.json()
        assert response_data == {
            "error": "Requested object not found.",
            "details": (
                f"{instance.__class__.__name__} #{instance.id} "
                f"does not exist or belongs to another user"
            ),
        }

    def assert_unauth(self, response: Response):
        response_data = self.assert_fail_response(response, status_code=401)
        assert response_data == {
            "error": "Authentication is required.",
            "details": "Invalid token header. No credentials provided.",
        }

    def assert_auth_invalid(
        self,
        response_data: Union[Response, dict],
        details: Optional[str],
        message: Optional[str] = None,
    ):
        if isinstance(response_data, Response):
            response_data = self.assert_fail_response(response_data, status_code=401)

        if message is None:
            message = "Authentication credentials are invalid."

        assert response_data == {
            "error": message,
            "details": details,
        }


class BaseTestWSAPI(BaseTestCase):
    url: str = NotImplemented

    @staticmethod
    def _get_headers(user_session: UserSession) -> dict:
        token_col = JWTSessionMixin._get_tokens(user_session.user, user_session.public_id)  # noqa
        return {"Authorization": f"Bearer {token_col.access_token}"}

    def _ws_request(
        self, client: TestClient, user_session: UserSession, data: dict | None = None
    ) -> dict | list:
        data = {"headers": self._get_headers(user_session)} | (data or {})
        with client.websocket_connect(self.url) as websocket:
            websocket.send_json(data)
            response_data = json.loads(websocket.receive_text())

        return response_data
