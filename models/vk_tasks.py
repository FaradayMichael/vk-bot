import datetime

from pydantic import BaseModel


class VkTaskFilterModel(BaseModel):
    from_dt: datetime.datetime | None = None
    to_dt: datetime.datetime | None = None
    methods_in: list[str] | None = None
    uuid_in: list[str] | None = None


class VkTask(BaseModel):
    uuid: str
    method: str
    args: dict | None
    kwargs: dict | None
    errors: str | None
    tries: int

    created: datetime.datetime
    started: datetime.datetime | None = None
    done: datetime.datetime | None = None

    ctime: datetime.datetime | None = None
