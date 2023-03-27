## About Constance

Constance is a port of django-constance library for django, implemented as a contrib library.
It is a key-value storage for global project-level constants, which can use various underlying backends.

### Plugging-in

- Define 2 settings in your settings.py-file:
  - settings.CONSTANCE_BACKEND - `str` - a string with path to constance backend class
  - settings.CONSTANCE_CONFIG - `Dict[str, Tuple[Any, str, Type]]` - a dict, where keys are constant keys, 
    and value is a 3-value tuple (default value, description, type)

If you are using `DatabaseBackend`, add `"starlette_web.contrib.constance.backends.database"` 
to `settings.INSTALLED_APPS`.

### Example

```python
import uuid
import datetime

INSTALLED_APPS = [
    ...,
    "starlette_web.contrib.constance.backends.database",
    ...
]

CONSTANCE_BACKEND = "starlette_web.contrib.constance.backends.database.DatabaseBackend"

CONSTANCE_CONFIG = {
    "TEST_CONSTANT_1": (1, "Test constant 1", int),
    "TEST_CONSTANT_2": (2, "Test constant 2", int),
    "TEST_CONSTANT_UUID": (uuid.UUID("094eb5ff-01de-4985-afeb-22ebb9e76abf"), "Test constant uuid", uuid.UUID),
    "TEST_CONSTANT_DATETIME": (datetime.datetime(2000, 1, 1), "Test constant datetime", datetime),
}
```

### Usage

```python
from starlette_web.contrib.constance import config

value = await config.get("TEST_CONSTANT_1")
values = await config.mget(["TEST_CONSTANT_1", "TEST_CONSTANT_2"])
for key, value in values.items():
    print(key, value)
    
await config.set("TEST_CONSTANT_1", 11)
```
