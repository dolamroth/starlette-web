import enum
from typing import Type

import sqlalchemy as sa
from sqlalchemy import Column
from sqlalchemy.sql import type_api as sa_type_api

from starlette_web.common.http.exceptions import ImproperlyConfigured
from starlette_web.common.database.types import ChoiceType
from starlette_web.common.utils.choices import Choices


# TODO: probably not supported in starlette_admin,
#  one has to manually set field converter to sqlalchemy implementation
#  in starlette_admin.contrib.sqla.helpers.converters
class ChoiceColumn(Column):
    """Just wrapper for ChoiceType db column

    >>> from sqlalchemy import String
    >>> from starlette_web.common.database import ModelBase
    >>> from starlette_web.common.utils.choices import TextChoices

    >>> class UserType(TextChoices):
    >>>    admin = 'admin'
    >>>    regular = 'regular'

    >>> class User(ModelBase):
    >>>     ...
    >>>     type = ChoiceColumn(UserType, impl=String(16), default=UserType.admin)

    >>> user = User(type='admin')
    >>> user.type
    [0] 'admin'

    """

    impl = sa.String(32)

    def __new__(
        cls, enum_class: Type[Choices], impl: sa_type_api.TypeEngine = None, *args, **kwargs
    ):
        if not issubclass(enum_class, Choices):
            raise ImproperlyConfigured(
                details=f"Enum class {enum_class} must be a subclass of "
                        f"starlette_web.common.utils.choices.Choices"
            )

        if "default" in kwargs:
            if isinstance(kwargs["default"], enum.Enum):
                kwargs["default"] = kwargs["default"].value

        if "nullable" not in kwargs:
            kwargs["nullable"] = False

        impl = impl or cls.impl
        return Column(ChoiceType(enum_class, impl=impl), *args, **kwargs)
