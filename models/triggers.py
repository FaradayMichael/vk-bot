import datetime

from pydantic import BaseModel

from models.answers import Answer
from models.base import (
    SuccessResponse
)


class TriggerCreate(BaseModel):
    value: str


class Trigger(TriggerCreate):
    id: int
    ctime: datetime.datetime

    answers: list[Answer] = []


class TriggerResponse(SuccessResponse):
    data: Trigger


class TriggersListResponse(SuccessResponse):
    data: list[Trigger]
