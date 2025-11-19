from datetime import datetime

from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import JSON, TIMESTAMP, Text, text

from .base import Base, utc_now_default


class VkTask(Base):
    __tablename__ = "vk_tasks"

    uuid: Mapped[str] = mapped_column(primary_key=True)
    func: Mapped[str]
    args: Mapped[dict | None] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    kwargs: Mapped[dict | None] = mapped_column(
        JSONB, server_default=text("'{}'::jsonb")
    )
    errors: Mapped[str | None] = mapped_column(Text, default=None)
    tries: Mapped[int]
    created: Mapped[datetime | None] = mapped_column(TIMESTAMP, default=None)
    started: Mapped[datetime | None] = mapped_column(TIMESTAMP, default=None)
    done: Mapped[datetime | None] = mapped_column(TIMESTAMP, default=None)
    ctime: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=utc_now_default)
