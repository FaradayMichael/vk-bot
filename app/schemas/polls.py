import datetime
from enum import IntEnum

from pydantic import BaseModel


class PollServices(IntEnum):
    VK = 0


class PollCreate(BaseModel):
    data: dict | None = None
    key: str
    service: PollServices | None = None


class Poll(PollCreate):
    id: int
    ctime: datetime.datetime
    atime: datetime.datetime | None = None
    dtime: datetime.datetime | None = None
