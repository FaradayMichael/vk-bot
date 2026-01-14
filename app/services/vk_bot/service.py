import asyncio
import datetime
import logging
import os
import traceback
from asyncio import AbstractEventLoop
from typing import (
    Callable,
    Coroutine,
)

from pydantic import ValidationError
from redis.asyncio import Redis
from redis.asyncio.client import PubSub
from vk_api.bot_longpoll import VkBotEventType

from app.business_logic import vk as vk_bl
from app.db import tasks as tasks_db
from app.db import send_on_schedule as send_on_schedule_db
from app.schemas.base import AttachmentType
from app.schemas.vk import Message
from app.schemas.vk.redis import RedisMessage, RedisCommands
from ...utils import redis
from app.utils.asynctask.serializer import JsonSerializer
from app.utils.asynctask.worker import Worker, Context
from app.utils.config import Config
from app.utils.consts import VK_SERVICE_REDIS_QUEUE
from app.utils.db import DBHelper, init_db
from app.utils.files import (
    TempBase64File,
    TempUrlFile,
    TempSftpFile,
    TempS3File,
)
from app.utils.service import BaseService
from app.utils.sftp import SftpClient
from app.utils.vk_client import VkClient

from .config import WORKER_QUEUE_NAME, VK_BOT_POST
from .models.asynctask import VkBotPost
from .models.service import BackgroundTasks
from .task import Task, save_task, execute_task
from app.services.utils.client import UtilsClient
from app.utils.s3 import S3Client

logger = logging.getLogger(__name__)


class VkBotService(BaseService):
    def __init__(
        self, config: Config, controller_name: str, loop: AbstractEventLoop, **kwargs
    ):
        super().__init__(config, controller_name, loop, **kwargs)

        self.db_helper: DBHelper | None = None
        self.redis_conn: Redis | None = None

        self._pubsub: PubSub | None = None
        self._commands_redis: dict[RedisCommands, Callable] = {}

        self.stopping: bool = True
        self._timeout = config.vk.timeout
        self.ex: list[Exception] = []
        self.last_ex: Exception | None = None
        self._queue: asyncio.Queue = asyncio.Queue()
        self._background_tasks: BackgroundTasks = BackgroundTasks()

        self.client_vk: VkClient | None = None
        self._handlers_vk: dict[VkBotEventType, Callable] = {}

        self.utils_client: UtilsClient | None = None
        self.asynctask_worker: Worker | None = None

        self.s3_client: S3Client | None = None

    @classmethod
    async def create(
        cls, config: Config, loop: asyncio.AbstractEventLoop, **kwargs
    ) -> "VkBotService":
        return await super().create(config, "vk_bot_service", loop, **kwargs)  # noqa

    async def init(self):
        self.db_helper = await init_db(self.config.db)
        self.redis_conn = await redis.init(self.config.redis)

        self.utils_client = await UtilsClient.create(self.amqp)
        self.asynctask_worker = await Worker.create(
            self.amqp, WORKER_QUEUE_NAME, JsonSerializer()
        )

        self.s3_client = S3Client(**self.config.s3.model_dump())
        await self.s3_client.init()

        self._register_handlers_vk()
        self._register_commands_redis()
        self._register_handlers_worker()

        self._pubsub = self.redis_conn.pubsub()
        await self._pubsub.subscribe(VK_SERVICE_REDIS_QUEUE)
        self._background_tasks.redis_listener = self.loop.create_task(
            self._listen_redis()
        )

    async def _main_task(self):
        logger.info("Starting main task")

        _tasks = []
        while not self.stopping:
            try:
                await self._allocate_vk(notify=True)

                _tasks = [
                    self.loop.create_task(self._listen_vk()),
                    self.loop.create_task(self._worker()),
                ]
                await asyncio.gather(*_tasks)

            except (
                GeneratorExit,
                asyncio.CancelledError,
                KeyboardInterrupt,
                StopIteration,
            ):
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
        logger.info(f"Starting VkBot worker")
        while not self.stopping:
            task: Task = await self._queue.get()

            if not isinstance(task, Task):
                raise TypeError(f"Invalid queue item: {task}")

            try:
                await execute_task(task)
                await self._save_task(task)
            except (GeneratorExit, asyncio.CancelledError, KeyboardInterrupt):
                break
            except Exception as e:
                if "Access denied" in str(e):
                    continue

                task.errors.append(traceback.format_exc())
                if task.tries <= 3:
                    await self._queue.put(task)
                else:
                    await self._save_task(task)
                raise

    async def execute_in_worker(self, func: Callable, *args, **kwargs):
        await self._queue.put(Task(func, *args, **kwargs))

    async def _listen_vk(self):
        logger.info("Start listening vk")
        while not self.stopping:
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

    async def on_vk_post(self, ctx: Context):

        async def handle_image(fp: str):
            attachments = await self.client_vk.upload.photo_wall(fp)
            return await vk_bl.post_in_group_wall(
                self.client_vk, attachments=attachments
            )

        async def handle_video(fp: str):
            return await self.client_vk.upload.video_wall_and_post(fp)

        async def handle_yt(link: str):
            return await vk_bl.post_yt_video(self.client_vk, link)

        message: VkBotPost = ctx.data
        if message.is_empty():
            logger.error("Empty MB message")
            return await ctx.success()

        if message.sftpUrl:
            logger.info(f"Handle {message.sftpUrl=}")
            async with SftpClient(self.config.sftp) as sftp_client:
                async with TempSftpFile(message.sftpUrl, sftp_client, True) as tmp:
                    attachment_type = AttachmentType.by_ext(
                        os.path.basename(tmp.filepath).split(".")[-1]
                    )
                    match attachment_type:
                        case AttachmentType.PHOTO:
                            await handle_image(tmp.filepath)
                        case AttachmentType.VIDEO:
                            await handle_video(tmp.filepath)
                        case _ as arg:
                            logger.error(f"Unsupported media type: {arg}")
            return await ctx.success()

        if message.bucket and message.filePath:
            logger.info(f"Handle {message.bucket=} {message.filePath=}")
            async with TempS3File(
                message.filePath, message.bucket, self.s3_client, True
            ) as tmp:
                attachment_type = AttachmentType.by_ext(
                    os.path.basename(tmp.filepath).split(".")[-1]
                )
                match attachment_type:
                    case AttachmentType.PHOTO:
                        await handle_image(tmp.filepath)
                    case AttachmentType.VIDEO:
                        await handle_video(tmp.filepath)
                    case _ as arg:
                        logger.error(f"Unsupported media type: {arg}")
            return await ctx.success()

        if message.yt_url:
            logger.info(f"Handle {message.yt_url=}")
            await handle_yt(message.yt_url)
            return await ctx.success()

        if message.base64:
            logger.info("Handle base64 message")
            if (
                AttachmentType.by_content_type(message.base64.mimetype)
                is AttachmentType.PHOTO
            ):
                async with TempBase64File(message.base64) as tmp:
                    await handle_image(tmp.filepath)
            else:
                logger.error(
                    f"Unsupported image base64 media type: {message.base64.mimetype}"
                )
            return await ctx.success()

        if message.video_url:
            logger.info(f"Handle {message.video_url=}")
            async with TempUrlFile(str(message.video_url)) as tmp:
                if tmp:
                    logger.info(tmp)
                    if (
                        AttachmentType.by_content_type(tmp.content_type)
                        is AttachmentType.VIDEO
                    ):
                        await handle_video(tmp.filepath)
                    else:
                        logger.error(
                            f"Unsupported video media type: {tmp.content_type}"
                        )
            return await ctx.success()

        if message.image_url:
            logger.info(f"Handle {message.image_url=}")
            async with TempUrlFile(str(message.image_url)) as tmp:
                if tmp:
                    if (
                        AttachmentType.by_content_type(tmp.content_type)
                        is AttachmentType.PHOTO
                    ):
                        await handle_image(tmp.filepath)
                    else:
                        logger.error(
                            f"Unsupported image media type: {tmp.content_type}"
                        )
            return await ctx.success()

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
                    if msg["data"] == 1:
                        continue

                    try:
                        model = RedisMessage.model_validate_json(msg["data"])
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
                message=Message(
                    text=f"Starting VkBot Service\nex: {self.last_ex}\ndebug: {self.config.debug}"
                ),
            )
            self.last_ex = None

    async def _release_vk(self):
        if self.client_vk:
            await self.client_vk.close()
            self.client_vk = None

    async def _save_task(self, task: Task):
        async with self.db_helper.get_session() as session:
            await save_task(session, task)

    async def _init_background_tasks(self):
        self.start_background_task(coro=self._main_task())
        await self.start_schedule_tasks()

    async def start_schedule_tasks(self):
        from .vk.sheduled import send_on_schedule

        logger.info("Starting send on schedule tasks")

        async with self.db_helper.get_session() as session:
            schedule_tasks = await send_on_schedule_db.get_list(session)
            for s_t in schedule_tasks:
                self.start_schedule_task(
                    coro=send_on_schedule(
                        self,
                        cron=s_t.cron,
                        peer_id=s_t.message_data["peer_id"],
                        message=Message(**s_t.message_data["message"]),
                    )
                )

        async def _get_daily_statistic_message_data(
            peer_id: int,
        ) -> tuple[int, Message]:
            now = datetime.datetime.now()
            async with self.db_helper.get_session() as db_session:
                tasks = await tasks_db.get_list(
                    db_session, from_dt=now - datetime.timedelta(days=1), to_dt=now
                )
            text = (
                f"Daily notify.\n"
                f"service ex: {self.ex[-1] if self.ex else ''}\n"
                f"tasks: {len(tasks)} with ex: {len([t for t in tasks if t.errors])}"
            )
            self.ex = []
            return peer_id, Message(text=text)

        self.start_schedule_task(
            coro=send_on_schedule(
                self,
                cron="0 6 * * *",
                fetch_message_data_func=_get_daily_statistic_message_data,
                args=(self.config.vk.main_user_id,),
            )
        )

    def stop_schedule_tasks(self):
        logger.info("Send on schedule stop called")
        for task in self._background_tasks.schedule_tasks:
            task.cancel()
        self._background_tasks.schedule_tasks = []

    def start_background_task(self, coro: Coroutine):
        self._background_tasks.tasks.append(self.loop.create_task(coro))
        logger.info(
            f"Register background task: {coro.__qualname__} {coro.cr_frame.f_locals}"
        )

    def start_schedule_task(self, coro: Coroutine):
        self._background_tasks.schedule_tasks.append(self.loop.create_task(coro))
        logger.info(
            f"Register schedule task: {coro.__qualname__} {coro.cr_frame.f_locals}"
        )

    def _register_handlers_vk(self):
        from .vk import handlers

        self.register_handler_vk(VkBotEventType.MESSAGE_NEW, handlers.on_new_message)
        self.register_handler_vk(
            VkBotEventType.MESSAGE_EVENT, handlers.on_callback_event
        )
        self.register_handler_vk(VkBotEventType.POLL_VOTE_NEW, handlers.on_poll_vote)
        self.register_handler_vk(VkBotEventType.MESSAGE_REPLY, handlers.on_message_reply)

    def register_handler_vk(self, method: VkBotEventType, handler: Callable):
        self._handlers_vk[method] = handler

    def _register_commands_redis(self):
        self._commands_redis[RedisCommands.SERVICE_START] = self.start_service
        self._commands_redis[RedisCommands.SERVICE_STOP] = self.stop_service
        self._commands_redis[RedisCommands.SERVICE_RESTART] = self.restart_service

    def _register_handlers_worker(self):
        self.asynctask_worker.register(VK_BOT_POST, self.on_vk_post, VkBotPost)

    async def start_service(self):
        logging.info(f"Starting VkBot Service")
        if self.stopping:
            self.stopping = False

            await self._init_background_tasks()

    async def stop_service(self):
        logger.info(f"VkBot Service stop calling")
        if not self.stopping:
            self.stopping = True

            self.stop_schedule_tasks()

            for task in self._background_tasks.tasks:
                task.cancel()
            self._background_tasks.tasks = []

            await self._release_vk()

    async def restart_service(self, timeout_seconds: int = 30):
        logger.info(f"Restart Srvice. Timeout seconds: {timeout_seconds}")
        await self.stop_service()
        await asyncio.sleep(timeout_seconds)
        await self.start_service()

    async def safe_close(self):
        try:
            await self.stop_service()
            await self.close()
        except Exception as e:
            logger.error(f"Closed with ex {e}")

    async def close(self):
        self._handlers_vk = {}

        if self._background_tasks.redis_listener:
            self._background_tasks.redis_listener.cancel()
            self._background_tasks.redis_listener = None

        self._commands_redis = {}

        if self._pubsub:
            await self._pubsub.aclose()
            self._pubsub = None

        if self.db_helper:
            await self.db_helper.close()
            self.db_helper = None

        if self.redis_conn:
            await redis.close(self.redis_conn)
            self.redis_conn = None

        if self.s3_client:
            await self.s3_client.close()
            self.s3_client = None

        if self.utils_client:
            await self.utils_client.close()
            self.utils_client = None

        if self.asynctask_worker:
            await self.asynctask_worker.close()
            self.asynctask_worker = None

        await super().close()
