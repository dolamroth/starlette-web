## Caching

Framework supports Django-like generic cache backend.
A sample implementation is provided for Redis in `starlette_web.contrib.redis.cache.RedisCache`,
and for local filesystem in `starlette_web.common.files.cache.FileCache`.

## Plugging-in

- Define the following parameter in your settings.py file:
  - settings.CACHES - a dictionary of dictionaries, containing key `BACKEND` 
  with string import to cache backend, and a key `OPTIONS`, 
  providing whatever options are required to instantiate cache backend.

Example:

```python
CACHES = {
    "default": {
        "BACKEND": "starlette_web.contrib.redis.RedisCache",
        "OPTIONS": {
            "host": "localhost",
            "port": 6379,
            "db": 0,
        },
    }
}
```

## Usage

```python
from starlette_web.common.caches import caches

value = await caches['default'].async_get('key')
await caches['default'].async_set('key', value, timeout=10)
```

## Locks

In addition to Django-like cache backend, BaseCache implementation provides named locks (mutexes).
Example of usage:

```python
from starlette_web.common.caches import caches

async with caches['default'].lock(
    'lock_name', 
    blocking_timeout=None, 
    timeout=1, 
    retry_interval=0.001,
):
    ...
```

Defaults:
- blocking_timeout = None (seconds)
- timeout = 20.0 (seconds)
- retry_interval = 0.001 (seconds)

**Important note**: custom locks in `starlette_web` have no deadlock detection, 
so use `timeout` parameter to avoid deadlocking.
