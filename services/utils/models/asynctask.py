from pydantic import BaseModel


class GptChat(BaseModel):
    user: int | str
    message_text: str


class GptChatResponse(BaseModel):
    message: str


class ImageUrl(BaseModel):
    url: str
