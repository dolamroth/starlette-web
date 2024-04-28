def test_empty_response(client):
    # This test covers ability of starlette-web to circumvent design of uvicorn library,
    # which forbids sending any request body for 204, 304 responses
    response = client.get("/empty/")
    assert response.content == b"null"


def test_endpoint_with_context_passed_to_schema(client):
    response = client.post("/context-schema/", json={"value": 9})
    assert response.content == b'{"value":101}'
