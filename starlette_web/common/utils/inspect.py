from typing import Callable, Any

import inspect


def get_available_options(_method: Callable, exclude=("self",)):
    full_args_spec = inspect.getfullargspec(_method)
    result = full_args_spec.args + full_args_spec.kwonlyargs
    return [arg for arg in result if arg not in exclude]


def safe_init(_klass, **options) -> Any:
    args = get_available_options(_klass.__init__)
    return _klass(**{key: value for key, value in options.items() if key in args})
