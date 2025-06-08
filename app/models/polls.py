from enum import Enum

from sqlalchemy import JSON, Integer
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .base import BaseTable

class PollServiceEnum(Enum):
    Discord = 0

class Poll(BaseTable):
    data: Mapped[dict | None] = mapped_column(JSONB)
    key: Mapped[str]
    service: Mapped[PollServiceEnum] = mapped_column(Integer,default=PollServiceEnum.Discord)
