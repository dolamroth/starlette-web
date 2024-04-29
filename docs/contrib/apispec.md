## OpenAPI documentation

Native starlette has [built-in support](https://www.starlette.io/schemas/) 
for generating openapi schemas (used by Swagger/Redoc).

`starlette_web` provides minor enhancements over original schema generation via `starlette_web.contrib.apispec`.

### Setting up

In settings file, include `starlette_web.contrib.apispec` to `settings.INSTALLED_APPS`.

```python
INSTALLED_APPS = [
    ...,
    "starlette_web.contrib.apispec",
    ...,
]
```

In settings file, also define `settings.APISPEC`. 
`CONFIG` matches options, passed at `apispec.APISpec` object initialization.

```python
APISPEC = {
    "CONFIG": dict(
        title="Project documentation",
        version="0.0.1",
        openapi_version="3.0.2",
        info=dict(description="My custom project."),
    ),
    "CONVERT_TO_CAMEL_CASE": False,
}
```

### Plugging-in

```python
from starlette.routing import Route
from starlette_web.contrib.apispec.views import OpenApiView

routes = [
    Route("/openapi", OpenApiView, include_in_schema=False)
]
```

Then, query GET endpoint with specifying GET-parameter `format` (by default, `openapi`):

- `openapi` - returns JSON-schema;
- `redoc` - [interactive API documentation](https://github.com/Redocly/redoc) from OpenAPI specification

`Swagger` is not supported as to version `0.1.x`.

### Introspection

`starlette_web.contrib.apispec` automatically:
- adds 401 response, if endpoint defines `auth_backend`
- populates security schemas `BaseAuthenticationBackend.openapi_name` and `BaseAuthenticationBackend.openapi_spec`
- adds 403 response, if endpoint defines `permission_classes`
- adds `Route` path parameters

### Schema validation

OpenAPI schema is validated with `openapi_spec_validator`. 
In general, this helps to find errors in YAML APIspec, 
such as missing path parameters or invalid indentation.

**Note**: Validation also <u>forbids user to create multiple subclasses `marshmallow.schema.Schema`
with the same class name</u>. The reason boils down to the fact, that marshmallow stores all schemas in
inner registry by class name. If any 2 classes have same name, APIspec struggles to choose exact
schema class for introspection and gives up. This results in invalid OpenAPI, where schema is mentioned,
but its definition is missing.

**Note**: Validation is performed on each `app` startup, which includes uvicorn worker restarts.
To disable validation in production, set `settings.SKIP_CHECKS` to `True` 
or use command line parameter `--skip_checks`.

### Camel case support

`contrib.camel_case` provides helper methods and classes to convert `snake_case` to `camelCase` and vice versa.
Use its `CamelCaseStarletteParser` and `CamelCaseJSONRenderer` as drop-in replacements for default 
`request_parser` and `response_renderer` of `BaseHttpEndpoint`.

Should you use it, also set `settings.APISPEC["CONVERT_TO_CAMEL_CASE"]` to `True`.

### Usage

Please, see `starlette_web.contrib.auth` and `starlette_web.tests.contrib.test_apispec` for examples of usage.

### TODO: More features will be available in 0.2.
