from enum import StrEnum
from typing import Any

from pydantic import (
    BaseModel,
    model_validator
)


class PhotoSize(BaseModel):
    height: int = 0
    width: int = 0
    type: str = ''
    url: str = ''


class PhotoAttachment(BaseModel):
    album_id: int = -1
    date: int = 0
    id: int = 0
    owner_id: int = 0
    access_key: str = ''
    sizes: list[PhotoSize] = []
    text: str = ''

    @model_validator(mode='after')
    def filter_max_size(self):
        if self.sizes:
            self.sizes = [max(self.sizes, key=lambda x: x.height)]
        return self

    @property
    def attachment_str(self) -> str:
        return f"photo{self.owner_id}_{self.id}"


class VideoAttachment(BaseModel):
    image: list[PhotoSize] = []


class WallAttachment(BaseModel):
    attachments: list["VkMessageAttachment"] = []


class VkMessageAttachment(BaseModel):
    type: str = ''
    photo: PhotoAttachment | None = None
    video: VideoAttachment | None = None
    wall: WallAttachment | None = None


class VkMessage(BaseModel):
    date: int = 0
    from_id: int = 0
    id: int = 0
    attachments: list[VkMessageAttachment] = []
    conversation_message_id: int = 0
    fwd_messages: list[Any] = []
    peer_id: int = 0
    text: str = ''


class WallItemFilter(StrEnum):
    POSTPONED = 'postponed'


class WallItem(BaseModel):
    comments: dict | None = None
    attachments: list[VkMessageAttachment] | None = None
    id: int
    text: str = ''
    post_source: dict | None = None
