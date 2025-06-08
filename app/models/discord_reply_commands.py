from sqlalchemy import Text, BigInteger
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class DiscordReplyCommand(Base):
    __tablename__ = 'discord_reply_commands'

    en: Mapped[bool] = mapped_column(default=True)
    command: Mapped[str] = mapped_column(primary_key=True)
    text: Mapped[str] = mapped_column(Text)
    reply: Mapped[bool] = mapped_column(default=False)
    channel_id: Mapped[int | None] = mapped_column(BigInteger, default=None)
