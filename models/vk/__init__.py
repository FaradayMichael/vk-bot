import logging
from enum import StrEnum

from pydantic import BaseModel


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
    message_text: str = ''
    attachments: str | None = None


class SendMessage(BaseModel):
    peer_id: int
    message: Message
