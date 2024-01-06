import asyncio
import logging
from asyncio import AbstractEventLoop
from pprint import pformat
from typing import Callable

from asyncpg import Pool
from pydantic import ValidationError

from vk_api.bot_longpoll import (
    VkBotLongPoll,
    VkBotEventType,
    VkBotMessageEvent
)

from business_logic.vk import parse_image_tags
from misc import (
    db
)

from misc.config import Config
from misc.vk_client import VkClient
from models.images import ImageTags
from models.vk import Message
from services.vk_bot.models import VkMessageAttachment, PhotoSize, VkMessage

logger = logging.getLogger(__name__)

backslash_n = '\n'  # Expression fragments inside f-strings cannot include backslashes


class VkBotService:
    def __init__(
            self,
            loop: AbstractEventLoop,
            config: Config,
            db_pool: Pool,
    ):
        self.loop: AbstractEventLoop = loop
        self.config: Config = config
        self.db_pool: Pool = db_pool

        self.stopping: bool = False
        self.ex: Exception | None = None
        self.task: asyncio.Task | None = None

        self.client: VkClient | None = None
        self.long_pool: VkBotLongPoll | None = None
        self.handlers: dict[VkBotEventType, Callable] = {}

    async def on_new_message(self, event: VkBotMessageEvent):
        try:
            message_model = VkMessage.model_validate(dict(event.message))
        except ValidationError as e:
            logger.exception(e)
            logger.info(event.message)
            return

        logger.info(pformat(message_model.model_dump()))

        tags_models: list[ImageTags] = []
        if message_model.attachments:
            images_urls = get_photos_urls_from_message(message_model.attachments)
            tags_models = [
                await parse_image_tags(i)
                for i in images_urls
            ]
        logger.info(f"{tags_models=}")
        if tags_models:
            await self.client.send_message(
                peer_id=message_model.peer_id if event.from_chat else message_model.from_id,
                message=Message(
                    text='\n\n'.join(
                        [
                            f'tags: {i.tags}{backslash_n + i.description if i.description else ""}'
                            for i in tags_models
                        ]
                    )
                )
            )

    async def bot_listen(self):
        logger.info("Start listening")
        async for event in self.events_generator():
            handler = self.handlers.get(event.type, None)
            if handler:
                logger.info(event.type)
                await handler(event)

    async def listen_task(self):
        logger.info("Start listening task")
        while not self.stopping:
            try:
                await self.allocate()
                await self.bot_listen()
            except (GeneratorExit, asyncio.CancelledError, KeyboardInterrupt):
                self.stop()
                break
            except Exception as e:
                logger.exception(e)
                self.ex = e

    async def allocate(self):
        logger.info("Allocate VkBotService...")
        self.client = await VkClient.create(self.config)
        self.long_pool = VkBotLongPoll(
            self.client.session,
            self.config.vk.main_group_id
        )
        await self.client.send_message(
            peer_id=self.config.vk.main_user_id,
            message=Message(text=f"Starting VkBpt Service\nLast ex: {self.ex}")
        )
        self.ex = None

    async def events_generator(self):
        while not self.stopping:
            for event in await asyncio.to_thread(self.long_pool.check):
                yield event

    @classmethod
    async def create(
            cls,
            loop: AbstractEventLoop,
            config: Config
    ) -> "VkBotService":
        db_pool = await db.init(config.db)

        instance = cls(loop, config, db_pool)

        return instance

    async def start(self):
        logging.info(f'Starting VkBot Service')

        self.register(VkBotEventType.MESSAGE_NEW, self.on_new_message)

        self.task = self.loop.create_task(
            self.listen_task()
        )

    def register(self, method: VkBotEventType, handler: Callable):
        self.handlers[method] = handler

    def stop(self):
        if not self.stopping:
            logger.info(f"VkBot Service stopping was planned")
            self.stopping = True

            self.loop.create_task(self.safe_close())

    async def safe_close(self):
        try:
            await self.close()
        except Exception as e:
            logger.exception(f'Closed with exception {e}')

    async def close(self):
        self.stopping = True

        if self.db_pool:
            await self.db_pool.close()
            self.db_pool = None

        if self.client:
            await self.client.close()
            self.client = None


def get_photos_urls_from_message(
        attachments: list[VkMessageAttachment]
) -> list[str]:
    result = []
    if attachments:
        for i in attachments:
            match i.type:
                case 'photo':
                    max_img = extract_max_size_img(i.photo.sizes)
                    result.append(max_img.url)

                case 'video':
                    max_img = extract_max_size_img(i.video.image)
                    result.append(max_img.url)

                case 'wall':
                    result += get_photos_urls_from_message(
                        attachments=i.wall.attachments
                    )
                case _:
                    logger.info(f"Unsupported attachment media: {i}")
    return result


def extract_max_size_img(sizes: list[PhotoSize]):
    return max(sizes, key=lambda x: x.height)
