import datetime
import uuid

from starlette_web.contrib.auth.utils import encode_jwt, decode_jwt


def test_jwt_utils():
    # Test, that StarletteJSONEncoder is used for jwt encoding
    payload = {
        "field": [1, 2.0, False, None, {"1": 2}],
        "user_id": uuid.uuid4(),
        "date": datetime.datetime.now(),
    }

    token, _ = encode_jwt(payload)
    assert type(token) is str
    assert token.count(".") == 2

    decoded = decode_jwt(token)
    assert "exp" in decoded
    assert "exp_iso" in decoded
    assert "token_type" in decoded
    assert decoded["field"] == payload["field"]
    assert decoded["user_id"] == str(payload["user_id"])
    assert decoded["date"] == payload["date"].isoformat()[:23]
