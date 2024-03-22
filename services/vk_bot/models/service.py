import asyncio

from pydantic import (
    BaseModel,
    model_validator,
    AnyUrl,
    ConfigDict
)

from misc.dataurl import DataURL

Task = asyncio.Task


class BackgroundTasks(BaseModel):
    redis_listener: Task | None = None
    schedule_tasks: list[Task] = []
    tasks: list[Task] = []

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @property
    def is_empty(self) -> bool:
        return bool(
            self.tasks or self.schedule_tasks or self.redis_listener
        )


class KafkaMessage(BaseModel):
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
