from pydantic import BaseModel


class KnowIds(BaseModel):
    id: int
    name: str
    vk_id: int | None = None
    note: str | None = None
    extra_data: dict | None = None
