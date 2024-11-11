import asyncio
import logging

from asyncpg import Pool
from redis.asyncio import Redis

from business_logic.images import parse_image_tags
from misc import (
    db,
    redis
)
from misc.asynctask.models import (
    ErrorData
)
from misc.asynctask.serializer import (
    JsonSerializer
)
from misc.asynctask.worker import (
    Worker,
    Context
)
from misc.config import Config
from misc.gigachat_client import (
    GigachatClient
)
from misc.service import (
    BaseService
)
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

# https://discordpy.readthedocs.io/en/stable/api.html

logger = logging.getLogger(__name__)


class UtilsService(BaseService):
    def __init__(
            self,
            config: Config,
            controller_name: str,
            loop: asyncio.AbstractEventLoop,
            **kwargs
    ):
        super().__init__(config, controller_name, loop, **kwargs)

        self.db_pool: Pool | None = None
        self.redis_conn: Redis | None = None

        self.gigachat_client: GigachatClient | None = None
        self.asynctask_worker: Worker | None = None

    async def on_get_image_tags(self, ctx: Context):
        data: ImageUrl = ctx.data
        logger.info(f"Handling image url: {data.url}")
        result = await parse_image_tags(data.url)
        await ctx.success(result)

    async def on_gpt_chat(self, ctx: Context):
        data: GptChat = ctx.data
        if not data.message_text:
            return await ctx.error(
                ErrorData(message='Message text is empty')
            )
        logger.info(f'Handle message: {data}')
        try:
            response_message = await self.gigachat_client.chat(data.user, data.message_text)
            if response_message:
                return await ctx.success(GptChatResponse(message=response_message.content))
            return await ctx.error(ErrorData(message='Failed to chat'))
        except Exception as e:
            logger.exception(e)
            return

    @classmethod
    async def create(
            cls,
            config: Config,
            loop: asyncio.AbstractEventLoop,
            **kwargs
    ) -> "UtilsService":
        return await super().create(config, 'utils_service', loop, **kwargs)  # noqa

    async def init(self):
        self.db_pool = await db.init(self.config.db)
        self.redis_conn = await redis.init(self.config.redis)
        self.gigachat_client = GigachatClient(self.config.gigachat, self.db_pool)

        self.asynctask_worker = await Worker.create(self.amqp, WORKER_QUEUE_NAME, JsonSerializer())
        self._register_handlers_worker()

    def _register_handlers_worker(self):
        self.asynctask_worker.register(
            GPT_CHAT,
            self.on_gpt_chat,
            GptChat
        )
        self.asynctask_worker.register(
            GET_IMAGE_TAGS,
            self.on_get_image_tags,
            ImageUrl
        )

    async def close(self):
        if self.db_pool:
            await db.close(self.db_pool)
            self.db_pool = None
        if self.redis_conn:
            await redis.close(self.redis_conn)
            self.redis_conn = None
        if self.gigachat_client:
            await self.gigachat_client.close()
            self.gigachat_client = None

        await super().close()
