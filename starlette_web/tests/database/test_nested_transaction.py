import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from starlette_web.contrib.auth.models import User
from starlette_web.tests.helpers import await_


def test_nested_transaction(dbs: AsyncSession):
    email = str(uuid.uuid4()).replace("-", "") + "@test.com"
    password = User.make_password(str(uuid.uuid4()))

    async def run_test():
        async with dbs.begin_nested() as block1:
            async with dbs.begin_nested() as block2:
                user = User(email=email, password=password)
                dbs.add(user)
                await dbs.flush()

                query = select(User).filter(User.email == email)
                user = (await dbs.execute(query)).scalars().first()
                assert user is not None

                await block2.commit()

            user = (await dbs.execute(query)).scalars().first()
            assert user is not None

            await block1.rollback()

        user = (await dbs.execute(query)).scalars().first()
        assert user is None

    await_(run_test())
