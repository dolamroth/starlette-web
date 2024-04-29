import json
import uuid


def test_empty_response(client):
    # This test covers ability of starlette-web to circumvent design of uvicorn library,
    # which forbids sending any request body for 204, 304 responses
    response = client.get("/empty/")
    assert response.content == b"null"


def test_endpoint_with_context_passed_to_schema(client):
    response = client.post("/context-schema/", json={"value": 9})
    assert response.content == b'{"value":101}'


def test_endpoint_with_typed_method_field(client):
    response = client.post("/typed-schema/", json={"method_value": [0, 0, 0, 0]})
    json_content = json.loads(response.content)
    assert "method_value" in json_content
    assert len(json_content["method_value"]) == 4
    for _u in json_content["method_value"]:
        assert 2**62 <= int(uuid.UUID(_u)) <= 2**63
