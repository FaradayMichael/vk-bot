from enum import StrEnum

from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.schemas.send_on_schedule import SendOnScheduleMessage
from .base import BaseTable


class SendOnScheduleServiceEnum(StrEnum):
    VK = 'vk'


class SendOnSchedule(BaseTable):
    __tablename__ = 'send_on_schedule'

    cron: Mapped[str]
    message_data: Mapped[SendOnScheduleMessage] = mapped_column(JSONB)
    service: Mapped[SendOnScheduleServiceEnum | None] = mapped_column(default=None)
