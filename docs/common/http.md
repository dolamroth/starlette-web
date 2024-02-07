## HttpEndpoint

`starlette_web` enforces usage of class-based endpoints. 
HttpEndpoints are loosely based on `APIView` from `djangorestframework`.

To create endpoint, subclass `starlette_web.common.http.base_endpoint.BaseHTTPEndpoint`.

`BaseHTTPEndpoint` provides helper methods `_validate` and `_response`, 
which act like `Serializer.validated_data` and `Response` classes from DRF.
These use schemas and parsers/renderers, defined on class level.
Their usage is optional.

Schemas are split into `request_schema` and `response_schema`. 
This is different from DRF, which provides a single schema for request and response.

### OpenAPI documentation

See [docs/apispec](../contrib/apispec.md)

### Routing

See [starlette documentation](https://www.starlette.io/endpoints/) on plugging class-based endpoints to routes.

### Exception raising and handling

A proper way to raise exception in `http` module is to raise a subclass of 
`starlette_web.common.http.exception.BaseApplicationError`, which supplies status code,
error description and optional error details. A number of subclasses with respective status codes 
are already defined in project.

**Note**: these exceptions may, but should not be raised in websocket routes. 
Instead, reraise those as `WebsocketDisconnect` exception.

Error details is supplied in any of the following cases:  
- `settings.APP_DEBUG` is True
- `settings.ERROR_DETAIL_FORCE_SUPPLY` is True
- `exc.status_code` == 400
