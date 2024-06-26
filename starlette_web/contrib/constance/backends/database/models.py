from sqlalchemy import LargeBinary, Column, String

from starlette_web.common.database import ModelBase


class Constance(ModelBase):
    __tablename__ = "constance"

    key = Column(String(length=255), primary_key=True)
    value = Column(LargeBinary(), nullable=True, default="")

    def __str__(self):
        return self.key
