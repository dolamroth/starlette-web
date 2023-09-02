from unittest.mock import patch

from starlette_web.tests.core.test_base import BaseTestAPIView


class TestHealthCheckAPIView(BaseTestAPIView):
    url = "/health_check/"

    def test_health__ok(self, client):
        response = client.get(self.url)
        response_data = self.assert_ok_response(response)
        assert response_data == {"services": {"postgres": "ok"}, "errors": []}

    @patch("starlette_web.common.authorization.permissions.AllowAnyPermission.has_permission")
    def test_health__fail(self, mock_filter, client):
        mock_filter.side_effect = RuntimeError("Oops")
        response = client.get(self.url)

        response_data = response.json()
        assert response.status_code == 503
        assert response_data == {
            "services": {"postgres": "down"},
            "errors": ["Couldn't connect to DB: RuntimeError 'Oops'"],
        }
