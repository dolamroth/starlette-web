def test_empty_response(client):
    # This test covers ability of starlette-web to circumvent design of uvicorn library,
    # which forbids sending any request body for 204, 304 responses
    response = client.get("/empty/")
    assert response.content == b"null"
