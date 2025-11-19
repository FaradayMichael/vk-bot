from datetime import datetime

from sqlalchemy import ForeignKey, TIMESTAMP, JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.services.vk_bot.models.vk import VkMessage
from .base import Base, utc_now_default
from .triggers_answers import TriggerAnswer


class TriggerHistory(Base):
    __tablename__ = "triggers_history"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    ctime: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=utc_now_default)
    trigger_answer_id: Mapped[int] = mapped_column(ForeignKey("triggers_answers.id"))
    vk_id: Mapped[int]
    message_data: Mapped[dict] = mapped_column(JSONB)

    trigger_answer: Mapped[TriggerAnswer] = relationship(TriggerAnswer, lazy="joined")

    @property
    def message_data_model(self) -> VkMessage:
        return VkMessage(**self.message_data)
