## Authentication and permissions

`starlette_web.common.authorization` contains definitions for base user, 
authentication backend and permission classes.

**BaseUserMixin** is designed to fit any model, that can represent a user.
It does not define database methods and does not inherit SQLAlchemy orm `declarative_base`.
An **AnonymousUser** is a special version of `BaseUserMixin`, that always returns False to `is_authenticated`.

**Authentication backend** accepts HttpConnection instance (Request/Websocket) 
and returns an instance of user or an AnonymousUser. 
It also seeds request scope with user instance. 
It is a shallow copy of authentication backend from Django Rest Framework. 
As to the latest version of starlette_web, you may only set a single backend on an endpoint.

**Permission class** accepts request and determines, whether user have respective permissions.
It raises `PermissionDeniedError` exception, if check is not passed. 
Any endpoint accepts list of permission classes, 
and you may combine them with boolean operations in the same way, as in DRF.

### Notes

- By default, any endpoint has `NoAuthenticationBackend` and empty list of permission classes.
- Authentication backends and permission classes work the same for BaseHttpEndpoint and BaseWSEndpoint alike.

### JWT utils

`encode_jwt` and `decode_jwt` (implemented with `PyJWT`) are provided in `starlette_web.common.authorization`.  

Syntax:  
- `encode_jwt(payload: dict, expires_in: int, **kwargs) -> str`
- `decode_jwt(token: str, **kwargs) -> dict`  

Default encoding algorithm is set as `settings.AUTH_JWT_ALGORITHM`.

### Contrib auth module

`starlette_web.contrib.auth` module provides additional 
utilities, endpoints and models for authorization and authentication.

*TODO: refactoring of starlette_web.contrib.auth is planned* 

### Examples

See `starlette_web.contrib.auth` and `starlette_web.tests.api.test_auth` for examples of usage.
