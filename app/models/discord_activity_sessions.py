from datetime import datetime

from sqlalchemy import (
    BigInteger,
    JSON,
    TIMESTAMP, text
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import (
    Mapped,
    mapped_column
)

from .base import Base, utc_now_default


class DiscordActivitySession(Base):
    __tablename__ = 'discord_activity_sessions'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    started_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=utc_now_default)
    finished_at: Mapped[datetime | None] = mapped_column(TIMESTAMP, default=None)
    user_id: Mapped[str] = mapped_column(index=True)
    user_name: Mapped[str]
    activity_name: Mapped[str]
    extra_data: Mapped[dict | None] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))

    def started_at_tz(self, tz: datetime.tzinfo = None) -> datetime | None:
        if tz:
            return self.started_at.astimezone(tz)
        else:
            return self.started_at

    def finished_at_tz(self, tz: datetime.tzinfo = None) -> datetime | None:
        if tz and self.finished_at:
            return self.finished_at.astimezone(tz)
        else:
            return self.finished_at
