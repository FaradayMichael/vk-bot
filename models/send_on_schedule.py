import datetime

from pydantic import BaseModel

from models.base import SuccessResponse
from models.vk import Message


class SendOnScheduleMessage(BaseModel):
    peer_id: int
    message: Message


class SendOnScheduleNew(BaseModel):
    cron: str
    message_data: SendOnScheduleMessage


class SendOnSchedule(SendOnScheduleNew):
    id: int
    ctime: datetime.datetime
    etime: datetime.datetime | None = None


class SendOnScheduleSuccessResponse(SuccessResponse):
    data: SendOnSchedule
