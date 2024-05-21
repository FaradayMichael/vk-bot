from pydantic import BaseModel, AnyUrl, model_validator

from misc.dataurl import DataURL


class MBMessage(BaseModel):
    base64: DataURL | None = None
    video_url: AnyUrl | None = None

    @model_validator(mode='before')
    def validate_empty(cls, data):
        if isinstance(data, dict):
            for k, v in data.items():
                data[k] = v or None
        return data

    def is_empty(self) -> bool:
        return not bool(self.model_dump(exclude_none=True))
