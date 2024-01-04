import datetime

from pydantic import BaseModel

from models.base import (
    SuccessResponse
)


class AnswerCreate(BaseModel):
    value: str


class Answer(AnswerCreate):
    id: int
    ctime: datetime.datetime


class AnswerResponse(SuccessResponse):
    data: Answer


class AnswersListResponse(SuccessResponse):
    data: list[Answer]
