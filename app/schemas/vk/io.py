from pydantic import BaseModel, model_validator

from app.utils.dataurl import DataURL
from app.schemas.base import SuccessResponse, AttachmentType
from app.schemas.vk import SendMessage
from app.services.vk_bot.models.vk import VkMessage


class AttachmentInput(BaseModel):
    type: AttachmentType
    file: DataURL


class MessageInput(BaseModel):
    text: str = None
    attachments: list[AttachmentInput] = None

    @model_validator(mode="after")
    def empty_model_validate(self):
        if not self.attachments:
            assert (
                self.text is not None
            ), "Field 'text' is required when 'attachments' is null"
        return self


class SendMessageInput(BaseModel):
    peer_id: int
    message: MessageInput


class SendMessageResponse(SuccessResponse):
    data: SendMessage


class WallPostInput(BaseModel):
    yt_url: str


class MessagesHistoryResponse(BaseModel):
    total: int
    items: list[VkMessage]
