import argparse
import datetime
from decimal import Decimal
import uuid
from typing import Callable, Union, Optional, Type


Number = Union[float, int, Decimal]
OptionalNum = Optional[Number]


def arg_uuid(arg_value: str) -> uuid.UUID:
    try:
        return uuid.UUID(arg_value)
    except (ValueError, TypeError):
        raise argparse.ArgumentTypeError("Invalid UUID value")


def arg_date(arg_value: str) -> datetime.date:
    try:
        return datetime.date.fromisoformat(arg_value)
    except ValueError:
        raise argparse.ArgumentTypeError("Invalid ISO date value")


def arg_datetime(arg_value: str) -> datetime.datetime:
    try:
        return datetime.datetime.fromisoformat(arg_value)
    except ValueError:
        raise argparse.ArgumentTypeError("Invalid ISO datetime value")


def arg_decimal(arg_value: str) -> Decimal:
    try:
        return Decimal(arg_value)
    except ValueError:
        raise argparse.ArgumentTypeError("Invalid decimal value")


def arg_range(
    _min=None,
    _max=None,
    _type: Type = int,
) -> Callable[[str], Number]:
    def validator(arg_value: str) -> Number:
        try:
            if _type == int:
                value = int(arg_value)
            elif _type == float:
                value = float(arg_value)
            elif _type == Decimal:
                value = Decimal(arg_value)
            else:
                raise argparse.ArgumentTypeError("Unsupported range type")
        except (ValueError, TypeError):
            raise argparse.ArgumentTypeError(f"String {arg_value} cannot be cast to {_type}")

        if _min is not None:
            if _min > value:
                raise argparse.ArgumentTypeError(f"Value is lower than _min = {_min}")

        if _max is not None:
            if _max < value:
                raise argparse.ArgumentTypeError(f"Value is higher than _max = {_max}")

        return value

    return validator
