import asyncio
import logging
from concurrent.futures.process import ProcessPoolExecutor

from redis.asyncio import Redis

from app.business_logic.images import parse_image_tags
from app.business_logic.speech_to_text import speech_to_text

from ...utils import redis
from app.utils.asynctask.models import ErrorData
from app.utils.asynctask.serializer import JsonSerializer
from app.utils.asynctask.worker import Worker, Context
from app.utils.config import Config
from app.utils.gigachat_client import GigachatClient
from app.utils.service import BaseService
from app.utils.db import DBHelper, init_db
from .config import (
    WORKER_QUEUE_NAME,
    GPT_CHAT,
    GET_IMAGE_TAGS,
    SPEECH_TO_TEXT,
)
from .models.asynctask import (
    GptChat,
    GptChatResponse,
    ImageUrl,
    SpeechToText,
    SpeechToTextResponse,
)
from .selenium import SeleniumHelper
from app.utils.files import TempBase64File

# https://discordpy.readthedocs.io/en/stable/api.html

logger = logging.getLogger(__name__)


class UtilsService(BaseService):
    def __init__(
        self,
        config: Config,
        controller_name: str,
        loop: asyncio.AbstractEventLoop,
        **kwargs,
    ):
        super().__init__(config, controller_name, loop, **kwargs)

        self.db_helper: DBHelper | None = None
        self.redis_conn: Redis | None = None

        self.gigachat_client: GigachatClient | None = None
        self.asynctask_worker: Worker | None = None
        self._selenium_helper: SeleniumHelper = SeleniumHelper(config)

    async def on_get_image_tags(self, ctx: Context):
        data: ImageUrl = ctx.data
        logger.info(f"Handling image url: {data.url}")
        result = await asyncio.to_thread(self._selenium_helper.get_image_tags, data.url)
        await ctx.success(result)

    async def on_gpt_chat(self, ctx: Context):
        data: GptChat = ctx.data
        if not data.message_text:
            return await ctx.error(ErrorData(message="Message text is empty"))
        logger.info(f"Handle message: {data}")
        try:
            response_message = await self.gigachat_client.chat(
                data.user, data.message_text
            )
            if response_message:
                return await ctx.success(
                    GptChatResponse(message=response_message.content)
                )
            return await ctx.error(ErrorData(message="Failed to chat"))
        except Exception as e:
            logger.exception(e)
            return

    async def on_speech_to_text(self, ctx: Context):
        data: SpeechToText = ctx.data
        logger.info(f"Handle message: {repr(data)}")
        async with TempBase64File(data.base64, decode=True) as tmp:
            with ProcessPoolExecutor() as executor:
                text = await self.loop.run_in_executor(
                    executor, speech_to_text, tmp.filepath
                )
                logger.info(f"Speach2Text result: {text}")
        await ctx.success(SpeechToTextResponse(text=text))

    @classmethod
    async def create(
        cls, config: Config, loop: asyncio.AbstractEventLoop, **kwargs
    ) -> "UtilsService":
        return await super().create(config, "utils_service", loop, **kwargs)  # noqa

    async def init(self):
        self.db_helper = await init_db(self.config.db)
        self.redis_conn = await redis.init(self.config.redis)
        self.gigachat_client = GigachatClient(self.config.gigachat, self.db_helper)

        self.asynctask_worker = await Worker.create(
            self.amqp, WORKER_QUEUE_NAME, JsonSerializer()
        )
        self._register_handlers_worker()

    def _register_handlers_worker(self):
        self.asynctask_worker.register(GPT_CHAT, self.on_gpt_chat, GptChat)
        self.asynctask_worker.register(GET_IMAGE_TAGS, self.on_get_image_tags, ImageUrl)
        self.asynctask_worker.register(
            SPEECH_TO_TEXT, self.on_speech_to_text, SpeechToText
        )

    async def close(self):
        if self.db_helper:
            await self.db_helper.close()
            self.db_helper = None
        if self.redis_conn:
            await redis.close(self.redis_conn)
            self.redis_conn = None
        if self.gigachat_client:
            await self.gigachat_client.close()
            self.gigachat_client = None

        await super().close()
