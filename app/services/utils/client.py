import aio_pika

from app.utils.asynctask.client import Client
from app.utils.asynctask.serializer import JsonSerializer
from app.schemas.images import ImageTags
from .config import (
    WORKER_QUEUE_NAME,
    GPT_CHAT,
    GET_IMAGE_TAGS
)
from .models.asynctask import (
    GptChat,
    GptChatResponse,
    ImageUrl
)


class UtilsClient(Client):

    @classmethod
    async def create(
            cls,
            conn: aio_pika.RobustConnection | aio_pika.Connection | aio_pika.abc.AbstractRobustConnection,
            **kwargs
    ) -> 'Client':
        return await super().create(conn, WORKER_QUEUE_NAME, JsonSerializer())

    async def get_image_tags(self, image_url: str) -> ImageTags:
        return await self.call(
            method=GET_IMAGE_TAGS,
            data=ImageUrl(url=image_url),
            response_class=ImageTags,
            expiration=90
        )

    async def gpt_chat(
            self,
            user: int | str,
            message_text: str
    ) -> GptChatResponse:
        return await self.call(
            method=GPT_CHAT,
            data=GptChat(
                user=user,
                message_text=message_text
            ),
            response_class=GptChatResponse,
            expiration=30
        )
