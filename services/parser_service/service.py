import asyncio
import logging
from asyncio import BaseEventLoop
from typing import (
    Callable,
    Awaitable,
    Any
)

from business_logic.images import parse_image_tags
from misc.asynctask.serializer import JsonSerializer
from misc.asynctask.worker import Worker, Context
from misc.config import Config
from misc.service import BaseService
from .config import (
    WORKER_QUEUE_NAME,
    GET_IMAGE_TAGS
)
from .models import (
    ImageUrl
)

logger = logging.getLogger(__name__)

OnCloseCallback = Callable[[], Awaitable[None] | Any]


class ParserService(BaseService):
    def __init__(
            self,
            config: Config,
            controller_name: str,
            loop: BaseEventLoop,
    ):
        super().__init__(
            config,
            controller_name,
            loop
        )
        self.worker: Worker | None = None

    @classmethod
    async def create(
            cls,
            config: Config,
            loop: asyncio.AbstractEventLoop,
            **kwargs
    ) -> 'ParserService':
        return await super().create(config, 'parser_service', loop, **kwargs)  # noqa

    async def init(self):
        self.worker = await Worker.create(self.amqp, WORKER_QUEUE_NAME, JsonSerializer())
        self.worker.register(
            GET_IMAGE_TAGS,
            self.on_get_image_tags,
            ImageUrl
        )

    async def on_get_image_tags(self, ctx: Context):
        data: ImageUrl = ctx.data
        print(data)
        result = await parse_image_tags(data.url)
        await ctx.success(result)

    async def close(self):
        if self.worker:
            await self.worker.close()
            self.worker = None

        await super().close()
