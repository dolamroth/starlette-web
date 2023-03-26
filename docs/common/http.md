## HttpEndpoint

`starlette_web` enforces usage of class-based endpoints. 
HttpEndpoints are loosely based on `APIView` from `djangorestframework`.

To create endpoint, subclass `starlette_web.common.http.base_endpoint.BaseHTTPEndpoint`.

`BaseHTTPEndpoint` provides helper classes `_validate` and `_response`, 
which act like `Serializer.validated_data` and `Response` classes from DRF.
These use schemas and parsers/renderers, defined on class level.

Schema is split between request_schema and response_schema. 
This is different from DRF, which provides a single schema for request and response.

### OpenAPI documentation

TODO: write

### Routing

See [starlette documentation](https://www.starlette.io/endpoints/) on plugging class-based endpoints to routes.
