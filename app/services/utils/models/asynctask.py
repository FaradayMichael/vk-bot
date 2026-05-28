from pydantic import BaseModel

from app.utils.dataurl import DataURL


class GptChat(BaseModel):
    user: int | str
    message_text: str


class GptChatResponse(BaseModel):
    message: str


class ImageUrl(BaseModel):
    url: str


class SpeechToText(BaseModel):
    filename: str
    base64: DataURL

    def __repr__(self):
        return f"{self.filename} {str(self.base64)[:30]}"


class SpeechToTextResponse(BaseModel):
    text: str
