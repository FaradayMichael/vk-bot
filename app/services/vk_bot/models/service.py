import asyncio

from pydantic import BaseModel, ConfigDict

Task = asyncio.Task


class BackgroundTasks(BaseModel):
    redis_listener: Task | None = None
    schedule_tasks: list[Task] = []
    tasks: list[Task] = []

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @property
    def is_empty(self) -> bool:
        return bool(self.tasks or self.schedule_tasks or self.redis_listener)
