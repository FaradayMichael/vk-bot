from datetime import datetime
from sqlalchemy import BigInteger, TIMESTAMP, text
from sqlalchemy.orm import DeclarativeBase, declared_attr, Mapped, mapped_column
from sqlalchemy.ext.asyncio import AsyncAttrs


utc_now_default = text("(NOW() at time zone 'utc')")


class Base(AsyncAttrs, DeclarativeBase):
    __abstract__ = True

    @declared_attr.directive
    def __tablename__(cls) -> str:
        return cls.__name__.lower() + "s"


class BaseTable(Base):
    __abstract__ = True

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    en: Mapped[bool] = mapped_column(default=True)
    ctime: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=utc_now_default)
    atime: Mapped[datetime | None] = mapped_column(
        TIMESTAMP, default=None, onupdate=utc_now_default
    )
    dtime: Mapped[datetime | None] = mapped_column(TIMESTAMP, default=None)
