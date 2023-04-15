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

### Usage

Please, see `starlette_web.contrib.auth` and `starlette_web.tests.contrib.test_apispec` for examples of usage.

### Camel case support

`contrib.camel_case` provides helper methods and classes to convert `snake_case` to `camelCase` and vice versa.
Use its `CamelCaseStarletteParser` and `CamelCaseJSONRenderer` as drop-in replacements for default 
`request_parser` and `response_renderer` of `BaseHttpEndpoint`.

Should you use it, also set `settings.APISPEC["CONVERT_TO_CAMEL_CASE"]` to `True`.

### TODO: More features will be available in 0.2.
