import datetime

from pydantic import BaseModel

from models.answers import Answer
from models.base import (
    SuccessResponse
)


class TriggerAnswerCreate(BaseModel):
    trigger: str
    answer: str


class TriggerAnswer(TriggerAnswerCreate):
    id: int
    ctime: datetime.datetime


class TriggerGroup(BaseModel):
    trigger: str
    answers: list[str]


class AnswerGroup(BaseModel):
    answer: str
    triggers: list[str]


class TriggerAnswerListResponse(SuccessResponse):
    data: list[TriggerAnswer]


class TriggerGroupListResponse(SuccessResponse):
    data: list[TriggerGroup]
