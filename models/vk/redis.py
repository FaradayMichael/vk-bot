from enum import StrEnum
from typing import Any

from pydantic import BaseModel


class RedisCommands(StrEnum):
    SERVICE_START = 'service_start'
    SERVICE_STOP = 'service_stop'
    SERVICE_RESTART = 'service_restart'


class RedisCommandData(BaseModel):
    data: dict[str, Any] | None = None


class RedisMessage(RedisCommandData):
    command: RedisCommands | None = None
