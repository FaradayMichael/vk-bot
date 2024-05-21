import asyncio
import logging
from pprint import pformat

from asyncpg import Pool
from discord import (
    Intents,
    Message,
    File
)
from discord.ext.commands import Bot
from redis.asyncio import Redis

from misc import (
    db,
    redis
)
from misc.config import Config

logger = logging.getLogger(__name__)


class DiscordService:
    def __init__(
            self,
            loop: asyncio.AbstractEventLoop,
            config: Config
    ):
        self.stopping: bool = False
        self.loop: asyncio.AbstractEventLoop = loop
        self.config: Config = config
        self.db_pool: Pool | None = None
        self.redis_conn: Redis | None = None

        self._intents: Intents | None = None
        self._bot: Bot | None = None
        self._bot_task: asyncio.Task | None = None

        self._service_channel_id: int = 937785155727294474
        self._tasks: list[asyncio.Task] = []

    @staticmethod
    async def create(
            loop: asyncio.AbstractEventLoop,
            config: Config
    ) -> "DiscordService":
        instance = DiscordService(loop, config)
        await instance.init()
        return instance

    async def init(self):
        self.db_pool = await db.init(self.config.db)
        self.redis_conn = await redis.init(self.config.redis)

        self._intents = Intents.all()
        self._intents.messages = True
        self._bot = Bot(command_prefix=">", intents=self._intents)
        self._register_commands()
        self._register_events()

    async def start(self):
        logger.info("Starting Discord Service")
        self.stopping = False
        await self.start_bot()
        self._start_schedule_tasks()

    async def start_bot(self) -> None:
        logger.info("Starting Discord Bot")
        if self._bot:
            self._bot_task = self.loop.create_task(self.run_bot(self._bot))
        while not self._bot.is_ready():
            logger.info("Waiting for Bot ready...")
            await asyncio.sleep(1)

    async def run_bot(self, bot: Bot) -> None:
        logger.info(f"Run Discord Bot")
        try:
            await bot.start(self.config.discord.token)
        except (GeneratorExit, asyncio.CancelledError, StopIteration):
            self.close()
        except Exception as e:
            logger.error(e)
            return

    def _start_schedule_tasks(self) -> None:
        from .scheduled import send_on_schedule
        self._tasks.append(
            self.loop.create_task(
                send_on_schedule(
                    self,
                    "* * * * *",
                    937785108696551546,
                    filepaths=["static/test.gif"]
                )
            )
        )

    def _register_commands(self) -> None:
        from . import commands
        self._bot.add_command(commands.test)

    def _register_events(self) -> None:

        async def on_message(message: Message):
            if not message.author.bot:
                await self._bot.process_commands(message)
                logger.info(f"{message=}")
                logger.info(f"{message.content=}")
                logger.info(f"{message.attachments=}")
                logger.info(f"{message.stickers=}")

        from . import events
        self._bot.event(events.on_ready)
        self._bot.event(on_message)
        self._bot.event(events.on_presence_update)

    async def stop_bot(self) -> None:
        logger.info("Stopping Discord Bot")
        if self._bot_task:
            self._bot_task.cancel()
            self._bot_task = None
            if self._bot and not self._bot.is_closed():
                await self._bot.close()
                self._bot = None

    @property
    def bot(self) -> Bot:
        return self._bot

    async def stop(self):
        logger.info(f"Discord Service stop calling")
        self.stopping = True
        for task in self._tasks:
            task.cancel()
        self._tasks.tasks = []
        await self.stop_bot()

    def close(self) -> asyncio.Task:
        logger.info(f"Discord Service closing was planned")
        return self.loop.create_task(self.save_close())

    async def save_close(self):
        try:
            await self.stop()
            await self._close()
        except Exception as e:
            logger.error(f"Discord Service closed with ex {e}")

    async def _close(self):
        if self.db_pool:
            await db.close(self.db_pool)
            self.db_pool = None
        if self.redis_conn:
            await redis.close(self.redis_conn)
            self.redis_conn = None