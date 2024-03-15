from enum import StrEnum
from typing import Any

from pydantic import (
    BaseModel,
    model_validator,
    AnyUrl
)

from misc.dataurl import DataURL


class PhotoSize(BaseModel):
    height: int = 0
    width: int = 0
    type: str = ''
    url: str = ''
    src: str = ''


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
    id: int = 0
    owner_id: int = 0
    user_id: int | None = 0
    type: str | None = None
    access_key: str = ''
    can_add: int = 0
    title: str | None = ''
    image: list[PhotoSize] = []


class DocPreview(BaseModel):
    photo: PhotoAttachment | None = None


class DocAttachment(BaseModel):
    access_key: str = ''
    date: int = 0
    ext: str = ''
    id: int = 0
    owner_id: int = 0
    preview: DocPreview | None = None


class WallAttachment(BaseModel):
    attachments: list["VkMessageAttachment"] = []


class VkMessageAttachment(BaseModel):
    type: str = ''
    photo: PhotoAttachment | None = None
    video: VideoAttachment | None = None
    wall: WallAttachment | None = None
    doc: DocAttachment | None = None


class VkMessage(BaseModel):
    date: int = 0
    from_id: int = 0
    id: int = 0
    attachments: list[VkMessageAttachment] = []
    conversation_message_id: int = 0
    fwd_messages: list[Any] = []
    peer_id: int = 0
    text: str = ''
    from_chat: bool


class WallItemFilter(StrEnum):
    POSTPONED = 'postponed'


class WallItem(BaseModel):
    comments: dict | None = None
    attachments: list[VkMessageAttachment] | None = None
    id: int
    text: str = ''
    post_source: dict | None = None


class KafkaMessage(BaseModel):
    base64: DataURL | None = None
    video_url: AnyUrl | None = None

    @model_validator(mode='before')
    def validate_empty(cls, data):
        if isinstance(data, dict):
            for k, v in data.items():
                data[k] = v or None
        return data
