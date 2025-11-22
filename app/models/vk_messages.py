from sqlalchemy import Integer, Boolean, Text, text as text_orm
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseTable

class VkMessage(BaseTable):

    __tablename__ = 'vk_messages'

    from_id:  Mapped[int] = mapped_column(Integer, index=True)
    peer_id: Mapped[int] = mapped_column(Integer, index=True)
    from_chat: Mapped[bool] = mapped_column(Boolean, nullable=False)
    from_bot: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    date: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    attachments: Mapped[dict] = mapped_column(JSONB, server_default=text_orm("'{}'::jsonb"))
    reply_message: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=None)
