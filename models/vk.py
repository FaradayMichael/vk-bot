import logging
from enum import StrEnum

from pydantic import BaseModel, model_validator

from misc.dataurl import DataURL
from models.base import SuccessResponse


class AttachmentType(StrEnum):
    PHOTO = "photo"
    DOC = "doc"

    @staticmethod
    def by_content_type(
            content_type: str
    ) -> "AttachmentType":
        match content_type:
            case 'image/png':
                return AttachmentType.PHOTO
            case "image/jpeg":
                return AttachmentType.PHOTO
            case "image/bmp":
                return AttachmentType.PHOTO
            case _ as arg:
                logging.info(f"{arg=}")
                return AttachmentType.DOC


class Message(BaseModel):
    text: str
    attachment: str | None = None


class WallPost(BaseModel):
    message: str = ''
    attachments: str | None = None


class AttachmentInput(BaseModel):
    type: AttachmentType
    file: DataURL


class MessageInput(BaseModel):
    text: str = None
    attachments: list[AttachmentInput] = None

    @model_validator(mode='after')
    def empty_model_validate(self):
        if not self.attachments:
            assert self.text is not None, "Field 'text' is required when 'attachments' is null"
        return self


class SendMessageInput(BaseModel):
    peer_id: int
    message: MessageInput


class SendMessage(BaseModel):
    peer_id: int
    message: Message


class SendMessageResponse(SuccessResponse):
    data: SendMessage


class ChatsListResponse(SuccessResponse):
    data: list[int]
