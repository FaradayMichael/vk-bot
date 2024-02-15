from pydantic import BaseModel


class KnowIds(BaseModel):
    id: int
    name: str
