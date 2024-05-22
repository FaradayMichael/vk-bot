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
from redis.asyncio.client import PubSub
from vk_api.bot_longpoll import (
    VkBotEventType
)

from business_logic import (
    vk as vk_bl
)
from db import (
    tasks as tasks_db,
    send_on_schedule as send_on_schedule_db
)
from misc import (
    db,
    redis
)
from misc.config import Config
from misc.consts import VK_SERVICE_REDIS_QUEUE
from misc.files import (
    TempBase64File,
    TempUrlFile
)
from misc.messages_broker import (
    BaseConsumer,
    MBProvider,
    MBMessage
)
from misc.vk_client import VkClient
from models.vk import (
    Message
)
from models.base import AttachmentType
from models.vk.redis import (
    RedisMessage,
    RedisCommands
)
from .models.service import (
    BackgroundTasks
)
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

        self._pubsub: PubSub | None = None
        self._commands_redis: dict[RedisCommands, Callable] = {}

        self._stopping: bool = True
        self._timeout = config.vk.timeout
        self.ex: list[Exception] = []
        self.last_ex: Exception | None = None
        self._queue: asyncio.Queue = asyncio.Queue()
        self._background_tasks: BackgroundTasks = BackgroundTasks()

        self.client_vk: VkClient | None = None
        self._handlers_vk: dict[VkBotEventType, Callable] = {}

    @classmethod
    async def create(
            cls,
            loop: AbstractEventLoop,
            config: Config
    ) -> "VkBotService":
        instance = VkBotService(loop, config)
        await instance._init()
        return instance

    async def start(self):
        logging.info(f'Starting VkBot Service')
        if self._stopping:
            self._stopping = False

            await self._init_background_tasks()

    async def stop(self):
        logger.info(f"VkBot Service stop calling")
        if not self._stopping:
            self._stopping = True

            self.stop_schedule_tasks()

            for task in self._background_tasks.tasks:
                task.cancel()
            self._background_tasks.tasks = []

            await self._release_vk()

    async def _init(self):
        self.db_pool = await db.init(self.config.db)
        self.redis_conn = await redis.init(self.config.redis)

        self._register_handlers_vk()
        self._register_commands_redis()

        self._pubsub = self.redis_conn.pubsub()
        await self._pubsub.subscribe(VK_SERVICE_REDIS_QUEUE)
        self._background_tasks.redis_listener = self.loop.create_task(self._listen_redis())

    async def _main_task(self):
        logger.info("Starting main task")

        _tasks = []
        while not self._stopping:
            try:
                await self._allocate_vk(notify=True)

                _tasks = [
                    self.loop.create_task(self._listen_vk()),
                    self.loop.create_task(self._worker()),
                ]
                await asyncio.gather(*_tasks)

            except (GeneratorExit, asyncio.CancelledError, KeyboardInterrupt, StopIteration):
                # self.close()
                break
            except Exception as e:
                logger.exception(e)
                self.last_ex = e
                self.ex.append(e)

                for task in _tasks:
                    task.cancel()
                _tasks = []

                await self._release_vk()
                await asyncio.sleep(self._timeout)

    async def _worker(self):
        logger.info(f'Starting VkBot worker')
        while not self._stopping:
            task: Task = await self._queue.get()

            if not isinstance(task, Task):
                raise TypeError(f"Invalid queue item: {task}")

            try:
                await execute_task(task)
                await save_task(self.db_pool, task)
            except (GeneratorExit, asyncio.CancelledError, KeyboardInterrupt):
                break
            except Exception as e:
                task.errors.append(e)
                if task.tries <= 3:
                    await self._queue.put(task)
                else:
                    await save_task(self.db_pool, task)
                raise

    async def execute_in_worker(
            self,
            func: Callable,
            *args,
            **kwargs
    ):
        await self._queue.put(
            Task(func, *args, **kwargs)
        )

    async def _listen_vk(self):
        logger.info("Start listening vk")
        while not self._stopping:
            try:
                async for event in self.client_vk.events_generator():
                    logger.info(event.type)
                    handler = self._handlers_vk.get(event.type, None)
                    if handler:
                        await self.execute_in_worker(handler, self, event)
            except (GeneratorExit, asyncio.CancelledError, KeyboardInterrupt):
                return
            except Exception:
                raise

    async def _listen_kafka(self):

        async def handle_message(message: MBMessage):
            if message.is_empty():
                logger.info("Empty MB message")
                return

            if message.base64:
                if AttachmentType.by_content_type(message.base64.mimetype) is AttachmentType.PHOTO:
                    async with TempBase64File(message.base64) as tmp:
                        attachments = await self.client_vk.upload.photo_wall([tmp.filepath])
                    await self.execute_in_worker(
                        vk_bl.post_in_group_wall,
                        self.client_vk,
                        attachments=attachments
                    )
                else:
                    logger.info(f"Unsupported media type: {message.base64.mimetype}")

            if message.video_url:
                logger.info(f"{message.video_url=}")
                async with TempUrlFile(str(message.video_url)) as tmp:
                    if tmp:
                        logger.info(tmp)
                        if AttachmentType.by_content_type(tmp.content_type) is AttachmentType.VIDEO:
                            await self.client_vk.upload.video_wall_and_post(tmp.filepath)
                        else:
                            logger.info(f"Unsupported media type: {tmp.content_type}")

        logger.info("MB listener started")
        while not self._stopping:
            try:
                consumer: BaseConsumer = await BaseConsumer.create(self.config, MBProvider.KAFKA)
                logger.info("MB consumer started")
            except Exception as e:
                logger.exception(e)
                await asyncio.sleep(30)
                continue

            try:
                async for msg in consumer.lister():
                    msg: MBMessage
                    await handle_message(msg)

            except (GeneratorExit, asyncio.CancelledError, KeyboardInterrupt):
                break
            except consumer.base_ex as e:
                logger.error(e)
                await asyncio.sleep(30)
            except Exception as e:
                logger.exception(e)
            finally:
                await consumer.close()
                logger.info("MB consumer stopped")

    async def _listen_redis(self):

        async def handle_message(message: RedisMessage):
            if message.is_empty():
                logger.info("Empty redis message")
                return

            command_call = None
            data = message.data or {}
            match message.command:
                case RedisCommands.SEND_ON_SCHEDULE_RESTART:
                    self.stop_schedule_tasks()
                    await self.start_schedule_tasks()
                case _:
                    command_call = self._commands_redis.get(message.command, None)

            if command_call:
                await command_call(**data)

        logger.info("Redis listener started")
        while True:
            try:

                async for msg in self._pubsub.listen():
                    logger.info(msg)
                    if msg['data'] == 1:
                        continue

                    try:
                        model = RedisMessage.model_validate_json(msg['data'])
                    except ValidationError as e:
                        logger.error(f"Invalid redis message value: {e}")
                        continue

                    await handle_message(model)

            except (GeneratorExit, asyncio.CancelledError, KeyboardInterrupt):
                logger.info("Cancelling redis listener")
                break
            except Exception as e:
                logger.exception(e)

    async def _allocate_vk(self, notify: bool = False):
        logger.info("Allocate VkBot Service...")
        if not self.client_vk:
            self.client_vk = VkClient(self.config.vk)
        if notify:
            await self.client_vk.messages.send(
                peer_id=self.config.vk.main_user_id,
                message=Message(text=f"Starting VkBot Service\nex: {self.last_ex}\ndebug: {self.config.debug}")
            )
            self.last_ex = None

    async def _release_vk(self):
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

        while not self._stopping:
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

                await self.execute_in_worker(self.client_vk.messages.send, peer_id, message)
            except (GeneratorExit, asyncio.CancelledError, KeyboardInterrupt):
                break
            except Exception as e:
                logger.exception(e)
                self.ex.append(e)
                await asyncio.sleep(300)

    async def _init_background_tasks(self):
        self.start_background_task(
            coro=self._main_task()
        )

        self.start_background_task(
            coro=self._listen_kafka()
        )

        await self.start_schedule_tasks()

    async def start_schedule_tasks(self):
        logger.info("Starting send on schedule tasks")

        schedule_tasks = await send_on_schedule_db.get_list(self.db_pool)
        for s_t in schedule_tasks:
            self.start_schedule_task(
                coro=self.send_on_schedule(
                    cron=s_t.cron,
                    peer_id=s_t.message_data.peer_id,
                    message=s_t.message_data.message
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

        self.start_schedule_task(
            coro=self.send_on_schedule(
                cron="0 6 * * *",
                fetch_message_data_func=_get_daily_statistic_message_data,
                args=(self.config.vk.main_user_id,)
            )
        )

    def stop_schedule_tasks(self):
        logger.info("Send on schedule stop called")
        for task in self._background_tasks.schedule_tasks:
            task.cancel()
        self._background_tasks.schedule_tasks = []

    def start_background_task(
            self,
            coro: Coroutine
    ):
        self._background_tasks.tasks.append(
            self.loop.create_task(
                coro
            )
        )
        logger.info(f"Register background task: {coro.__qualname__} {coro.cr_frame.f_locals}")

    def start_schedule_task(
            self,
            coro: Coroutine
    ):
        self._background_tasks.schedule_tasks.append(
            self.loop.create_task(
                coro
            )
        )
        logger.info(f"Register schedule task: {coro.__qualname__} {coro.cr_frame.f_locals}")

    def _register_handlers_vk(self):
        from .vk import handlers
        self.register_handler_vk(VkBotEventType.MESSAGE_NEW, handlers.on_new_message)
        self.register_handler_vk(VkBotEventType.MESSAGE_EVENT, handlers.on_callback_event)

    def register_handler_vk(self, method: VkBotEventType, handler: Callable):
        self._handlers_vk[method] = handler

    def _register_commands_redis(self):
        self._commands_redis[RedisCommands.SERVICE_START] = self.start
        self._commands_redis[RedisCommands.SERVICE_STOP] = self.stop
        self._commands_redis[RedisCommands.SERVICE_RESTART] = self.restart

    async def restart(self, timeout_seconds: int = 30):
        logger.info(f"Restart Srvice. Timeout seconds: {timeout_seconds}")
        await self.stop()
        await asyncio.sleep(timeout_seconds)
        await self.start()

    def close(self) -> asyncio.Task:
        logger.info(f"VkBot Service closing was planned")
        return self.loop.create_task(self.save_close())

    async def save_close(self):
        try:
            await self.stop()
            await self._close()
        except Exception as e:
            logger.error(f"Closed with ex {e}")

    async def _close(self):
        self._handlers_vk = {}

        if self._background_tasks.redis_listener:
            self._background_tasks.redis_listener.cancel()
            self._background_tasks.redis_listener = None

        self._commands_redis = {}

        if self._pubsub:
            await self._pubsub.aclose()
            self._pubsub = None

        if self.db_pool:
            await self.db_pool.close()
            self.db_pool = None

        if self.redis_conn:
            await redis.close(self.redis_conn)
            self.redis_conn = None
