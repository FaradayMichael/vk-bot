from datetime import datetime

from sqlalchemy import (
    BigInteger,
    String,
    TIMESTAMP,
    text,
    ForeignKey,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
)

from app.models.base import Base, utc_now_default


class SteamUser(Base):
    __tablename__ = "steam_users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    steam_id: Mapped[str] = mapped_column(
        String, nullable=False, unique=True, index=True
    )
    username: Mapped[str] = mapped_column(String, nullable=True, default=None)

    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, server_default=utc_now_default
    )
    extra_data: Mapped[dict | None] = mapped_column(
        JSONB, server_default=text("'{}'::jsonb")
    )


class SteamActivitySession(Base):
    __tablename__ = "steam_activity_sessions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    started_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, server_default=utc_now_default
    )
    finished_at: Mapped[datetime | None] = mapped_column(TIMESTAMP, default=None)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("steam_users.id"), nullable=False, index=True
    )
    steam_id: Mapped[str] = mapped_column(String, nullable=False)
    activity_name: Mapped[str]
    extra_data: Mapped[dict | None] = mapped_column(
        JSONB, server_default=text("'{}'::jsonb")
    )

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


class SteamStatusSession(Base):
    __tablename__ = "steam_status_sessions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    started_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, server_default=utc_now_default
    )
    finished_at: Mapped[datetime | None] = mapped_column(TIMESTAMP, default=None)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("steam_users.id"), nullable=False, index=True
    )
    steam_id: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str]
    extra_data: Mapped[dict | None] = mapped_column(
        JSONB, server_default=text("'{}'::jsonb")
    )

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
