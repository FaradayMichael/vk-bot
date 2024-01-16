import asyncio
import datetime
import logging
from asyncio import AbstractEventLoop
from typing import Callable

from asyncpg import Pool

from vk_api.bot_longpoll import (
    VkBotLongPoll,
    VkBotEventType
)

from misc import (
    db
)

from misc.config import Config
from misc.vk_client import VkClient
from models.vk import Message

logger = logging.getLogger(__name__)


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
        self.ex: list[Exception] = []
        self.main_task: asyncio.Task | None = None
        self.background_tasks: list[asyncio.Task] = []

        self.client: VkClient | None = None
        self.long_pool: VkBotLongPoll | None = None
        self.handlers: dict[VkBotEventType, Callable] = {}

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

        from . import handlers
        self.register_handler(VkBotEventType.MESSAGE_NEW, handlers.on_new_message)

        self.register_background_task(
            func=self.send_on_schedule_task,
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

        self.main_task = self.loop.create_task(
            self.listen_task()
        )

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
                message=Message(text=f"Starting VkBot Service\nex: {self.ex}")
            )
            self.ex = []

    async def release(self):
        if self.client:
            await self.client.close()
            self.client = None
        if self.long_pool:
            self.long_pool = None

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
                self.ex.append(e)
                await self.release()
                await asyncio.sleep(30)

    async def bot_listen(self):
        logger.info("Start listening")
        async for event in self.events_generator():
            handler = self.handlers.get(event.type, None)
            if handler:
                logger.info(event.type)
                await handler(self, event)

    async def events_generator(self):
        while not self.stopping:
            for event in await asyncio.to_thread(self.long_pool.check):
                yield event

    async def send_on_schedule_task(
            self,
            peer_id: int,
            message: Message,
            start_time: datetime.time,
            weekday: int | None = None
    ):
        success = True
        while not self.stopping:
            try:
                await self.allocate(notify=False)

                if success:
                    sleep = get_sleep_seconds(start_time, weekday)
                    logger.info(f"{sleep=}")
                    await asyncio.sleep(sleep)

                await self.client.send_message(peer_id, message)
                success = True
            except (GeneratorExit, asyncio.CancelledError, KeyboardInterrupt):
                break
            except Exception as e:
                logger.exception(e)
                self.ex.append(e)
                await asyncio.sleep(60)
                await self.release()
                success = False

    def register_handler(self, method: VkBotEventType, handler: Callable):
        self.handlers[method] = handler

    def register_background_task(
            self,
            func: Callable,
            *args,
            **kwargs
    ):
        self.background_tasks.append(
            self.loop.create_task(
                func(*args, **kwargs)
            )
        )
        logger.info(f"Register schedule task {func} {args=} {kwargs=}")

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

        self.handlers = {}

        if self.db_pool:
            await self.db_pool.close()
            self.db_pool = None

        await self.release()


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
