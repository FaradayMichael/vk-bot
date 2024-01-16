import asyncio
import datetime
import logging
import random
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
from db import (
    triggers_answers as triggers_answers_db
)
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
        self.background_tasks: list[asyncio.Task] = []

        self.client: VkClient | None = None
        self.long_pool: VkBotLongPoll | None = None
        self.handlers: dict[VkBotEventType, Callable] = {}

    async def on_new_message(self, event: VkBotMessageEvent):
        message_model = validate_message(event)
        if not message_model:
            return

        logger.info(pformat(message_model.model_dump()))
        from_chat = event.from_chat
        peer_id = message_model.peer_id if event.from_chat else message_model.from_id
        from_id = message_model.from_id

        tags_models = await parse_attachments_tags(message_model.attachments)
        logger.info(f"{tags_models=}")
        if tags_models:
            await self.client.send_message(
                peer_id=peer_id,
                message=Message(
                    text='\n\n'.join(
                        [
                            f'tags: {i.tags_text}{backslash_n + i.description if i.description else ""}'
                            for i in tags_models
                        ]
                    )
                )
            )

        async with self.db_pool.acquire() as conn:
            find_triggers = await triggers_answers_db.get_for_like(
                conn,
                f"{message_model.text}{''.join([t.tags_text + str(t.description) for t in tags_models])}"
            )
            logger.info(find_triggers)
            answers = list(set(
                sum([i.answers for i in find_triggers], [])
            ))
            if answers:
                await self.client.send_message(
                    peer_id=peer_id,
                    message=Message(
                        text=f"{f'@id{from_id} ' if from_chat else ''} {random.choice(answers)}"
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
                await self.release()
                await asyncio.sleep(10)

    async def allocate(self, notify: bool = True):
        logger.info("Allocate VkBotService...")
        if not self.client:
            self.client = await VkClient.create(self.config)
        if not self.long_pool:
            self.long_pool = VkBotLongPoll(
                self.client.session,
                self.config.vk.main_group_id
            )
        if notify:
            await self.client.send_message(
                peer_id=self.config.vk.main_user_id,
                message=Message(text=f"Starting VkBot Service\nLast ex: {self.ex}")
            )
        self.ex = None

    async def release(self):
        if self.client:
            await self.client.close()
            self.client = None
        if self.long_pool:
            self.long_pool = None

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
        await self.allocate(notify=False)

        self.register_handler(VkBotEventType.MESSAGE_NEW, self.on_new_message)

        self.register_background_task(
            method=self.send_on_schedule,
            start_time=datetime.time(hour=9, minute=0),
            weekday=1,
            peer_id=2000000003,
            message=Message(
                text='',
                attachment=await self.client.upload_doc_message(
                    peer_id=2000000003,
                    doc_path='static/test.gif'
                )
            )
        )

        self.task = self.loop.create_task(
            self.listen_task()
        )

    def register_handler(self, method: VkBotEventType, handler: Callable):
        self.handlers[method] = handler

    def register_background_task(
            self,
            method: Callable,
            *args,
            **kwargs
    ):
        self.background_tasks.append(
            self.loop.create_task(
                method(*args, **kwargs)
            )
        )
        logger.info(f"Register schedule task {method}")

    async def send_on_schedule(
            self,
            peer_id: int,
            message: Message,
            start_time: datetime.time,
            weekday: int | None = None
    ):
        while True:
            try:
                await self.allocate(notify=False)
                sleep = get_sleep_seconds(start_time, weekday)
                logger.info(f"{sleep=}")
                await asyncio.sleep(sleep)
                await self.client.send_message(peer_id, message)
            except (GeneratorExit, asyncio.CancelledError, KeyboardInterrupt):
                break
            except Exception as e:
                logger.exception(e)
                await self.release()
                await asyncio.sleep(10)

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

        for task in self.background_tasks:
            task.cancel()
        if self.background_tasks:
            await asyncio.wait(self.background_tasks)
        self.background_tasks = []

        if self.db_pool:
            await self.db_pool.close()
            self.db_pool = None

        await self.release()


async def parse_attachments_tags(
        attachments: list[VkMessageAttachment]
) -> list[ImageTags]:
    if not attachments:
        return []
    images_urls = get_photos_urls_from_message(attachments)
    return [
        await parse_image_tags(i)
        for i in images_urls
    ]


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


def get_sleep_seconds(
        start_time: datetime.time,
        weekday: int | None = None,
) -> float:
    now = datetime.datetime.utcnow()

    if weekday is None:
        start = datetime.datetime(
            year=now.year,
            month=now.month,
            day=now.day,
            hour=start_time.hour,
            minute=start_time.minute
        )
        if start <= now:
            start = start + datetime.timedelta(days=1)
    else:
        days = weekday - now.weekday()
        days = 7 - now.weekday() + weekday if days < 0 else days
        start = datetime.datetime(
            year=now.year,
            month=now.month,
            day=now.day,
            hour=start_time.hour,
            minute=start_time.minute
        )
        start = start + datetime.timedelta(days=days)
        if start <= now:
            start = start + datetime.timedelta(days=7)

    return (start - now).total_seconds()


def validate_message(
        event: VkBotMessageEvent
) -> VkMessage | None:
    try:
        return VkMessage.model_validate(dict(event.message))
    except ValidationError as e:
        logger.exception(e)
        logger.info(event.message)
        return None
