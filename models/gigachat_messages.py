from datetime import datetime

from sqlalchemy import TIMESTAMP, Text, JSON, func, text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, utc_now_default


class GigachatMessage(Base):
    __tablename__ = 'gigachat_messages'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    ctime: Mapped[datetime] = mapped_column(TIMESTAMP,server_default=utc_now_default)
    user_id: Mapped[str] = mapped_column(index=True)
    id_: Mapped[str | None] = mapped_column(default=None)
    role: Mapped[str | None] = mapped_column(default=None)
    content: Mapped[str | None] = mapped_column(Text, default=None)
    function_call: Mapped[dict | None] = mapped_column(JSON, default=None)
    name: Mapped[str | None] = mapped_column(default=None)
    attachments: Mapped[dict | None] = mapped_column(JSON, default=None)
    data_for_context: Mapped[dict | None] = mapped_column(JSON, default=None)
