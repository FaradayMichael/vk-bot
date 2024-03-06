import asyncio
import datetime
import logging
from asyncio import AbstractEventLoop
from typing import (
    Callable,
    Coroutine,
    Any,
    Awaitable
)

import croniter as croniter
from aiokafka import (
    AIOKafkaConsumer,
    ConsumerRecord
)
from aiokafka.errors import KafkaError
from asyncpg import Pool
from pydantic import ValidationError
from redis.asyncio import Redis
from vk_api.bot_longpoll import (
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
from models.vk import Message, AttachmentType
from .models import KafkaMessage
from .task import (
    Task,
    save_task,
    execute_task
)

logger = logging.getLogger(__name__)


class VkBotService:
    def __init__(
            self,
            loop: AbstractEventLoop,
            config: Config
    ):
        self.loop: AbstractEventLoop = loop
        self.config: Config = config
        self.db_pool: Pool | None = None
        self.redis_conn: Redis | None = None

        self.stopping: bool = False
        self.timeout = config.vk.timeout
        self.ex: list[Exception] = []
        self.last_ex: Exception | None = None
        self.queue: asyncio.Queue = asyncio.Queue()
        self.background_tasks: list[asyncio.Task] = []

        self.client_vk: VkClient | None = None
        self.handlers_vk: dict[VkBotEventType, Callable] = {}

    @classmethod
    async def create(
            cls,
            loop: AbstractEventLoop,
            config: Config
    ) -> "VkBotService":
        instance = VkBotService(loop, config)
        await instance.init()
        return instance

    async def init(self):
        self.db_pool = await db.init(self.config.db)
        self.redis_conn = await redis.init(self.config.redis)
        self.register_handlers_vk()

    async def start(self):
        logging.info(f'Starting VkBot Service')
        await self.allocate_vk(notify=False)
        self.init_background_tasks()

    async def main_task(self):
        logger.info("Starting main task")

        _tasks = []
        while not self.stopping:
            try:
                await self.allocate_vk()

                _tasks = [
                    self.loop.create_task(self.listen_vk()),
                    self.loop.create_task(self.worker()),
                ]
                await asyncio.gather(*_tasks)

            except (GeneratorExit, asyncio.CancelledError, KeyboardInterrupt, StopIteration):
                self.stop()
                break
            except Exception as e:
                logger.exception(e)
                self.last_ex = e
                self.ex.append(e)

                for task in _tasks:
                    task.cancel()
                _tasks = []

                await self.release_vk()
                await asyncio.sleep(self.timeout)

    async def worker(self):
        logging.info(f'Starting VkBot worker')
        while not self.stopping:
            task: Task = await self.queue.get()

            if not isinstance(task, Task):
                logger.info(f"Invalid task: {task}")
                continue

            try:
                await self.handle_task(task)
            except (GeneratorExit, asyncio.CancelledError, KeyboardInterrupt):
                break
            except Exception:
                raise

    async def handle_task(self, task: Task):
        try:
            await execute_task(task)
            await save_task(self.db_pool, task)
        except (GeneratorExit, asyncio.CancelledError, KeyboardInterrupt):
            raise
        except Exception as e:
            task.errors.append(e)
            if task.tries <= 3:
                await self.queue.put(task)
            else:
                await save_task(self.db_pool, task)
            raise

    async def listen_vk(self):
        logger.info("Start listening vk")
        while not self.stopping:
            try:
                async for event in self.client_vk.events_generator():
                    logger.info(event.type)
                    handler = self.handlers_vk.get(event.type, None)
                    if handler:
                        await self.queue.put(Task(handler, self, event))
            except (GeneratorExit, asyncio.CancelledError, KeyboardInterrupt):
                return
            except Exception:
                raise

    async def listen_kafka(self):

        async def handle_message(message: KafkaMessage):
            if message.base64:
                if AttachmentType.by_content_type(message.base64.mimetype) is not AttachmentType.PHOTO:
                    logger.info(f"Unsupported media type: {message.base64.mimetype}")
                    return

                async with TempBase64File(message.base64) as tmp:
                    attachments = await self.client_vk.upload.photo_wall([tmp])
                await self.queue.put(
                    Task(
                        vk_bl.post_in_group_wall,
                        self.client_vk,
                        attachments=attachments
                    )
                )

        logger.info("Kafka listener started")
        while not self.stopping:
            consumer = AIOKafkaConsumer(
                *self.config.kafka.topics,
                bootstrap_servers=self.config.kafka.bootstrap_servers,
                loop=self.loop,
                retry_backoff_ms=30000
            )

            try:
                await consumer.start()
                logger.info("Kafka consumer started")

                async for msg in consumer:
                    msg: ConsumerRecord
                    logger.info(f"{msg.key=} {msg.topic=}")

                    try:
                        model = KafkaMessage.model_validate_json(msg.value)
                    except ValidationError as e:
                        logger.error(f"Invalid message value: {e}")
                        continue

                    await handle_message(model)

            except (GeneratorExit, asyncio.CancelledError, KeyboardInterrupt):
                break
            except KafkaError as e:
                logger.error(e)
                await asyncio.sleep(30)
            finally:
                await consumer.stop()
                logger.info("Kafka consumer stopped")

    async def allocate_vk(self, notify: bool = True):
        logger.info("Allocate VkBot Service...")
        if not self.client_vk:
            self.client_vk = VkClient(self.config)
        if notify:
            await self.client_vk.messages.send(
                peer_id=self.config.vk.main_user_id,
                message=Message(text=f"Starting VkBot Service\nex: {self.last_ex}\ndebug: {self.config.debug}")
            )
            self.last_ex = None

    async def release_vk(self):
        if self.client_vk:
            await self.client_vk.close()
            self.client_vk = None

    async def send_on_schedule(
            self,
            cron: str,

            peer_id: int | None = None,
            message: Message | None = None,

            fetch_message_data_func: Callable[[Any | None], Awaitable[tuple[int, Message]]] | None = None,
            args: tuple = (),
            kwargs: dict | None = None
    ):
        if kwargs is None:
            kwargs = {}

        while not self.stopping:
            try:
                if (peer_id is None or message is None) and fetch_message_data_func is None:
                    raise ValueError("One of (peer_id, message) or fetch_message_data_func is required")

                now = datetime.datetime.now()
                nxt: datetime.datetime = croniter.croniter(cron, now).get_next(datetime.datetime)
                sleep = (nxt - now).total_seconds()
                logger.info(f"Schedule {sleep=} {peer_id=} {message=} {fetch_message_data_func=}")
                await asyncio.sleep(sleep)

                peer_id, message = await fetch_message_data_func(
                    *args, **kwargs
                ) if fetch_message_data_func else (peer_id, message)

                await self.queue.put(Task(self.client_vk.messages.send, peer_id, message))
            except (GeneratorExit, asyncio.CancelledError, KeyboardInterrupt):
                break
            except Exception as e:
                logger.exception(e)
                self.ex.append(e)
                await asyncio.sleep(300)

    def init_background_tasks(self):
        self.start_background_task(
            coro=self.main_task()
        )

        async def _get_weekly_message_data(peer_id: int) -> tuple[int, Message]:
            key = "get_weekly_message_data-attachment"
            attachment = await redis.get(self.redis_conn, key)
            logger.info(f'from redis: {attachment=}')
            if not attachment:
                attachment = await self.client_vk.upload.doc_message(peer_id=peer_id, doc_path='static/test.gif')
                await redis.set(self.redis_conn, key, {'value': attachment})
            else:
                attachment = attachment['value']
            return peer_id, Message(
                text='',
                attachment=attachment
            )

        self.start_background_task(
            coro=self.send_on_schedule(
                cron="0 9 * * 2",
                fetch_message_data_func=_get_weekly_message_data,
                args=(2000000003,)
            )
        )

        async def _get_daily_statistic_message_data(peer_id: int) -> tuple[int, Message]:
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
            return peer_id, Message(
                text=text
            )

        self.start_background_task(
            coro=self.send_on_schedule(
                cron="0 6 * * *",
                fetch_message_data_func=_get_daily_statistic_message_data,
                args=(self.config.vk.main_user_id,)
            )
        )

        self.start_background_task(
            coro=self.listen_kafka()
        )

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

    def register_handlers_vk(self):
        from .vk import handlers
        self.register_handler_vk(VkBotEventType.MESSAGE_NEW, handlers.on_new_message)
        self.register_handler_vk(VkBotEventType.MESSAGE_EVENT, handlers.on_callback_event)

    def register_handler_vk(self, method: VkBotEventType, handler: Callable):
        self.handlers_vk[method] = handler

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
        self.background_tasks = []

        self.handlers_vk = {}

        if self.db_pool:
            await self.db_pool.close()
            self.db_pool = None

        if self.redis_conn:
            await redis.close(self.redis_conn)
            self.redis_conn = None

        await self.release_vk()
