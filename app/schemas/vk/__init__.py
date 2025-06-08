from pydantic import BaseModel


class Message(BaseModel):
    text: str
    attachment: str | None = None


class WallPost(BaseModel):
    message_text: str = ''
    attachments: str | None = None


class SendMessage(BaseModel):
    peer_id: int
    message: Message
