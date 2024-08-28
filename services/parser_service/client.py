import aio_pika

from misc.asynctask.client import Client
from misc.asynctask.serializer import JsonSerializer
from models.images import ImageTags
from .config import (
    WORKER_QUEUE_NAME,
    GET_IMAGE_TAGS
)
from .models import ImageUrl


class ParserClient(Client):

    @classmethod
    async def create(
            cls,
            conn: aio_pika.RobustConnection | aio_pika.Connection,
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
