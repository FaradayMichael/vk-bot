from datetime import datetime

from sqlalchemy import TIMESTAMP, JSON, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, utc_now_default


class DynamicConfig(Base):
    __tablename__ = 'dynamic_config'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    data: Mapped[dict] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    atime: Mapped[datetime | None] = mapped_column(TIMESTAMP,default=None, onupdate=utc_now_default)
