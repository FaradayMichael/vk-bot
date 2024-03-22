from enum import StrEnum
from typing import Any

from pydantic import BaseModel


class RedisCommands(StrEnum):
    SERVICE_START = 'service_start'
    SERVICE_STOP = 'service_stop'
    SERVICE_RESTART = 'service_restart'
    SEND_ON_SCHEDULE_RESTART = 'send_on_schedule_restart'


class RedisCommandData(BaseModel):
    data: dict[str, Any] | None = None


class RedisMessage(RedisCommandData):
    command: RedisCommands | None = None

    def is_empty(self) -> bool:
        return not bool(self.model_dump(exclude_none=True))
