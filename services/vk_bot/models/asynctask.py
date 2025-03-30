from pydantic import BaseModel, AnyUrl, model_validator

from utils.dataurl import DataURL


class VkBotPost(BaseModel):
    base64: DataURL | None = None
    video_url: AnyUrl | None = None
    sftpUrl: str | None = None
    image_url: AnyUrl | None = None
    yt_url: str | None = None

    @model_validator(mode='before')
    def validate_empty(cls, data):
        if isinstance(data, dict):
            for k, v in data.items():
                data[k] = v or None
        return data

    def is_empty(self) -> bool:
        return not bool(self.model_dump(exclude_none=True))
