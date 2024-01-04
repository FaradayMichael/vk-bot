from enum import StrEnum

from pydantic import BaseModel

from misc.dataurl import DataURL
from models.base import SuccessResponse


class AttachmentType(StrEnum):
    PHOTO = "photo"
    DOC = "doc"


class Message(BaseModel):
    text: str
    attachment: str | None = None


class AttachmentInput(BaseModel):
    type: AttachmentType
    file: DataURL


class MessageInput(BaseModel):
    text: str = None
    attachments: list[AttachmentInput] = None


class SendMessageInput(BaseModel):
    peer_id: int
    message: MessageInput


class ChatsListResponse(SuccessResponse):
    data: list[int]
