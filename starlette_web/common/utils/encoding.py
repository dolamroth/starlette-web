from typing import AnyStr


def force_str(value: AnyStr) -> str:
    try:
        return value.decode()
    except (UnicodeDecodeError, AttributeError):
        return str(value)
