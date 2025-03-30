from enum import StrEnum

from sqlalchemy import JSON
from sqlalchemy.orm import Mapped, mapped_column

from schemas.send_on_schedule import SendOnScheduleMessage
from .base import BaseTable


class SendOnScheduleServiceEnum(StrEnum):
    VK = 'vk'


class SendOnSchedule(BaseTable):
    __tablename__ = 'send_on_schedule'

    cron: Mapped[str]
    message_data: Mapped[SendOnScheduleMessage] = mapped_column(JSON)
    service: Mapped[SendOnScheduleServiceEnum | None] = mapped_column(default=None)
