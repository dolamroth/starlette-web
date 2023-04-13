## OpenAPI documentation

Native starlette has [built-in support](https://www.starlette.io/schemas/) 
for generating openapi schemas (used by Swagger/Redoc).

`starlette_web` provides minor enhancements over original schema generation via `starlette_web.contrib.apispec`.

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

### TODO: More features will be available in 0.2.
