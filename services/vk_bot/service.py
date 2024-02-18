import asyncio
import datetime
import logging
from asyncio import AbstractEventLoop
from typing import (
    Callable,
    AsyncIterable,
    Coroutine
)

from aiokafka import (
    AIOKafkaConsumer,
    ConsumerRecord
)
import croniter as croniter
from asyncpg import Pool
from pydantic import ValidationError
from redis.asyncio import Redis

from vk_api.bot_longpoll import (
    VkBotLongPoll,
    VkBotEventType
)

from business_logic import (
    vk as vk_bl
)
from db import (
    tasks as tasks_db
)
from misc import (
    db,
    redis
)

from misc.config import Config
from misc.files import TempBase64File
from misc.vk_client import VkClient
from models.vk import Message
from .models import KafkaMessage
from .task import Task

logger = logging.getLogger(__name__)


class VkBotService:
    def __init__(
            self,
            loop: AbstractEventLoop,
            config: Config,
            db_pool: Pool,
            redis_conn: Redis
    ):
        self.loop: AbstractEventLoop = loop
        self.config: Config = config
        self.db_pool: Pool = db_pool
        self.redis_conn: Redis = redis_conn

        self.stopping: bool = False
        self.ex: list[Exception] = []
        self.queue: asyncio.Queue = asyncio.Queue()
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
        redis_conn = await redis.init(config.redis)

        return VkBotService(loop, config, db_pool, redis_conn)

    async def start(self):
        logging.info(f'Starting VkBot Service')
        await self.allocate(notify=False)

        self.register_handlers()

        self.init_background_tasks()

        self.main_task = self.loop.create_task(
            self.worker()
        )

    async def worker(self):
        async def generate_from_queue(queue: asyncio.Queue) -> AsyncIterable[Task]:
            while True:
                try:
                    t: Task = await queue.get()
                    yield t
                    await t.save(self.db_pool)
                except (GeneratorExit, asyncio.CancelledError, KeyboardInterrupt, StopIteration):
                    if self.stopping:
                        logger.info("VkBot worker stop called")
                        break

        logging.info(f'Starting VkBot worker')
        while not self.stopping:
            await self.allocate()
            async for task in generate_from_queue(self.queue):
                try:
                    await task
                except (GeneratorExit, asyncio.CancelledError, KeyboardInterrupt):
                    self.stop()
                    break
                except Exception as e:
                    logger.exception(e)
                    self.ex.append(e)
                    task.errors.append(e)
                    if task.tries <= 3:
                        await self.queue.put(task)
                    else:
                        await task.save(self.db_pool)
                    await self.release()
                    await asyncio.sleep(30)
                    break

    async def listen_task(self):
        logger.info("Start listening task")
        while not self.stopping:
            try:
                await self.allocate(notify=False)
                await self.bot_listen()
            except (GeneratorExit, asyncio.CancelledError, KeyboardInterrupt):
                break
            except Exception as e:
                if not isinstance(e, AttributeError):
                    logger.exception(e)
                    self.ex.append(e)
                await self.release()
                await asyncio.sleep(30)

    async def bot_listen(self):
        logger.info("Start listening")
        async for event in self.events_generator():
            logger.info(event.type)
            handler = self.handlers.get(event.type, None)
            if handler:
                await self.queue.put(Task(handler, self, event))

    async def events_generator(self):
        while not self.stopping:
            for event in await asyncio.to_thread(self.long_pool.check):
                yield event

    async def base_background_task(
            self,
            func: Callable,
            *args,
            **kwargs,
    ):
        while not self.stopping:
            try:
                await func(*args, **kwargs)
            except (GeneratorExit, asyncio.CancelledError, KeyboardInterrupt):
                break
            except Exception as e:
                logger.exception(e)
                self.ex.append(e)

    async def send_on_schedule(
            self,
            # peer_id: int,
            # message: Message,
            cron: str,
            fetch_message_data_func: Callable,
            *args,
            **kwargs
    ):
        now = datetime.datetime.now()
        nxt: datetime.datetime = croniter.croniter(cron, now).get_next(datetime.datetime)
        sleep = (nxt - now).total_seconds()
        logger.info(f"Schedule {sleep=} {fetch_message_data_func=}")
        await asyncio.sleep(sleep)

        peer_id, message = await fetch_message_data_func(*args, **kwargs)

        await self.queue.put(Task(self.client.messages.send, peer_id, message))

    async def listen_kafka(
            self
    ):
        consumer = AIOKafkaConsumer(
            *self.config.kafka.topics,
            bootstrap_servers=self.config.kafka.bootstrap_servers,
            loop=self.loop
        )
        await consumer.start()
        logger.info("Kafka consumer started")
        try:
            async for msg in consumer:
                msg: ConsumerRecord
                logger.info(msg.key)
                try:
                    model = KafkaMessage.model_validate_json(msg.value)
                    async with TempBase64File(model.base64) as tmp:
                        attachments = await self.client.upload.photo_wall([tmp])
                    await self.queue.put(
                        Task(
                            vk_bl.post_in_group_wall,
                            self.client,
                            attachments=attachments
                        )
                    )
                except ValidationError as e:
                    logger.exception(e)
        except Exception as e:
            logger.exception(e)
            await consumer.stop()
            raise

    async def allocate(self, notify: bool = True):
        logger.info("Allocate VkBot Service...")
        if not self.client:
            self.client = VkClient(self.config)
        if not self.long_pool:
            self.long_pool = VkBotLongPoll(
                self.client.session_group,
                self.config.vk.main_group_id
            )
        if notify:
            await self.client.messages.send(
                peer_id=self.config.vk.main_user_id,
                message=Message(text=f"Starting VkBot Service\nex: {self.ex}\ndebug: {self.config.debug}")
            )
            self.ex = []

    async def release(self):
        if self.client:
            await self.client.close()
            self.client = None
        if self.long_pool:
            await asyncio.to_thread(self.long_pool.session.close)
            self.long_pool = None

    def init_background_tasks(self):
        self.start_background_task(
            coro=self.listen_task()
        )

        async def _get_weekly_message_data(peer_id: int) -> tuple[int, Message]:
            key = "get_weekly_message_data-attachment"
            attachment = await redis.get(self.redis_conn, key)
            logger.info(f'from redis: {attachment=}')
            if not attachment:
                attachment = await self.client.upload.doc_message(peer_id=peer_id, doc_path='static/test.gif')
                await redis.set(self.redis_conn, key, {'value': attachment})
            else:
                attachment = attachment['value']
            return peer_id, Message(
                text='',
                attachment=attachment
            )

        self.start_background_task(
            coro=self.base_background_task(
                func=self.send_on_schedule,
                cron="0 9 * * 2",
                fetch_message_data_func=_get_weekly_message_data,
                peer_id=2000000003
            )
        )

        async def _get_daily_statistic_message_data() -> tuple[int, Message]:
            now = datetime.datetime.now()
            async with self.db_pool.acquire() as conn:
                tasks = await tasks_db.get_list(
                    conn,
                    from_dt=now - datetime.timedelta(days=1),
                    to_dt=now
                )
            text = f"Daily notify.\n" \
                   f"service ex: {self.ex}\n" \
                   f"tasks: {len(tasks)} with ex: {len([t for t in tasks if t.errors])}"
            self.ex = []
            return self.config.vk.main_user_id, Message(
                text=text
            )

        self.start_background_task(
            coro=self.base_background_task(
                func=self.send_on_schedule,
                cron="0 6 * * *",
                fetch_message_data_func=_get_daily_statistic_message_data
            )
        )

        self.start_background_task(
            coro=self.base_background_task(
                func=self.listen_kafka
            )
        )

    def register_handlers(self):
        from . import handlers
        self.register_handler_vk(VkBotEventType.MESSAGE_NEW, handlers.on_new_message)
        self.register_handler_vk(VkBotEventType.MESSAGE_EVENT, handlers.on_callback_event)

    def register_handler_vk(self, method: VkBotEventType, handler: Callable):
        self.handlers[method] = handler

    def start_background_task(
            self,
            coro: Coroutine
    ):
        self.background_tasks.append(
            self.loop.create_task(
                coro
            )
        )
        logger.info(f"Register background task {coro} ")

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

        self.main_task.cancel()
        await self.main_task

        for task in self.background_tasks:
            task.cancel()
        if self.background_tasks:
            await asyncio.wait(self.background_tasks)
        self.background_tasks = []

        self.handlers = {}

        if self.db_pool:
            await self.db_pool.close()
            self.db_pool = None

        if self.redis_conn:
            await redis.close(self.redis_conn)
            self.redis_conn = None

        await self.release()
