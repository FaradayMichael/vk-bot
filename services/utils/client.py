import aio_pika

from misc.asynctask.client import Client
from misc.asynctask.serializer import JsonSerializer
from .config import (
    WORKER_QUEUE_NAME,
    GPT_CHAT
)
from .models.asynctask import (
    GptChat,
    GptChatResponse
)


class UtilsClient(Client):

    @classmethod
    async def create(
            cls,
            conn: aio_pika.RobustConnection | aio_pika.Connection,
            **kwargs
    ) -> 'Client':
        return await super().create(conn, WORKER_QUEUE_NAME, JsonSerializer())

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
