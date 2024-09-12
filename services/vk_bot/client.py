import aio_pika

from misc.asynctask.client import Client
from misc.asynctask.serializer import JsonSerializer
from misc.dataurl import DataURL
from .config import (
    WORKER_QUEUE_NAME,
    VK_BOT_POST
)
from .models.asynctask import VkBotPost


class VkBotClient(Client):

    @classmethod
    async def create(
            cls,
            conn: aio_pika.RobustConnection | aio_pika.Connection,
            **kwargs
    ) -> 'Client':
        return await super().create(conn, WORKER_QUEUE_NAME, JsonSerializer())

    async def vk_bot_post(
            self,
            base64: DataURL | None = None,
            video_url: str | None = None,
            sftp_url: str | None = None,
            image_url: str | None = None,
            yt_url: str | None = None,
    ):
        return await self.call(
            method=VK_BOT_POST,
            data=VkBotPost(
                base64=base64,
                video_url=video_url,
                sftpUrl=sftp_url,
                image_url=image_url,
                yt_url=yt_url,
            ),
            response_class=None,
            expiration=30
        )
