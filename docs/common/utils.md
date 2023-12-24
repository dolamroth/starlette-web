## Utilities

### decorator_from_middleware

Django-like [decorator_from_middleware](https://docs.djangoproject.com/en/5.0/ref/utils/#module-django.utils.decorators)
is not directly implemented, but may be replicated with Starlette's support for per-route middleware. See 
`starlette_web.tests.views.http.EndpointWithCacheMiddleware` and 
`starlette_web.tests.views.middlewares.CacheMiddleware` for example of usage.
