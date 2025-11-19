from enum import Enum
from typing import (
    TypeVar,
)
from pydantic import BaseModel, Field

ModelClass = TypeVar("ModelClass", bound=BaseModel)


METHOD_HEADER = "x-method"


class MessageType(str, Enum):
    REQUEST = "request"
    SUCCESS = "success"
    CANCELED = "canceled"
    EXCEPTION = "exception"
    ERROR = "error"
    NO_HANDLER = "no_handler"


class ExceptionType(str, Enum):
    NETWORK = "network"
    KNOWN = "known"
    UNKNOWN = "unknown"


class ExceptionData(BaseModel):
    cls: str
    message: str
    t: ExceptionType
    data: dict | None = Field(default_factory=dict)


class ErrorData(BaseModel):
    message: str
