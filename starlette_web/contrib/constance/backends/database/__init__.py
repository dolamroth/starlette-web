from typing import Dict, Any, List

from sqlalchemy import select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

from starlette_web.common.database import make_session_maker
from starlette_web.contrib.constance.backends.base import BaseConstanceBackend
from starlette_web.contrib.constance.backends.database.models import Constance


class DatabaseBackend(BaseConstanceBackend):
    session_maker: sessionmaker

    def __init__(self):
        super().__init__()
        # Disable connection pooling to avoid creating persistent open connections
        self.session_maker = make_session_maker(use_pool=False)

    async def mget(self, keys: List[str]) -> Dict[str, Any]:
        async with self.session_maker() as session:
            query = select(Constance)

            constants = (await session.execute(query)).scalars()
            values = {key: self.empty for key in keys}
            values = {
                **values,
                **{
                    constant.key: self._preprocess_response(constant.value)
                    for constant in constants
                    if constant.key in keys
                },
            }
            return values

    async def get(self, key: str) -> Any:
        async with self.session_maker() as session:
            query = select(Constance).filter(Constance.key == key)
            val = (await session.execute(query)).scalars().first()
            return self._preprocess_response(val.value if val else None)

    async def set(self, key: str, value: Any) -> None:
        async with self.session_maker() as session:
            query = select(Constance).filter(Constance.key == key).with_for_update()
            instance = (await session.execute(query)).scalars().first()

            if instance is None:
                try:
                    instance = Constance(
                        key=key,
                        value=self.serializer.serialize(value),
                    )
                    session.add(instance)
                    await session.commit()
                except IntegrityError:
                    # This case may occur, if multiple processes try
                    # to update an existing value at the same time
                    # TODO: examine, whether this could be processes in a better way
                    pass

            else:
                instance.value = self.serializer.serialize(value)
                await session.commit()
