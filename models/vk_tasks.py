from pydantic import BaseModel


class VkTask(BaseModel):
    uuid: str
    method: str
    args: str | None
    kwargs: dict | None
    errors: str | None
    tries: int
