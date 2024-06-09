from pydantic import BaseModel


class ReplyCommand(BaseModel):
    command: str
    text: str
    reply: bool = True
    channel_id: int | None = None
