import asyncio
import logging

from asyncpg import Pool
from discord import (
    Intents,
    Message
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
        self.loop: asyncio.AbstractEventLoop = loop
        self.config: Config = config
        self.db_pool: Pool | None = None
        self.redis_conn: Redis | None = None

        self._intents: Intents | None = None
        self._bot: Bot | None = None
        self._bot_task: asyncio.Task | None = None

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
        self._register_commands(self._bot)
        self._register_events(self._bot)

    async def start(self):
        logger.info("Starting Discord Service")
        await self.start_bot()

    async def start_bot(self) -> None:
        logger.info("Starting Discord Bot")
        if self._bot:
            self._bot_task = self.loop.create_task(self.run_bot(self._bot))

    async def run_bot(self, bot: Bot) -> None:
        logger.info(f"Run Discord Bot")
        try:
            await bot.start(self.config.discord.token)
        except (GeneratorExit, asyncio.CancelledError, StopIteration):
            return
        except Exception as e:
            logger.error(e)
            return

    @staticmethod
    def _register_commands(bot: Bot) -> Bot:
        from . import commands
        bot.add_command(commands.test)
        return bot

    def _register_events(self, bot: Bot) -> Bot:

        async def on_message(message: Message):
            await self._bot.process_commands(message)
            logger.info(f"{message=}")
            logger.info(f"{message.content=}")
            logger.info(f"{message.attachments=}")
            logger.info(f"{message.stickers=}")

        from . import events
        bot.event(events.on_ready)
        bot.event(on_message)
        bot.event(events.on_presence_update)
        return bot

    async def stop_bot(self) -> None:
        logger.info("Stopping Discord Bot")
        if self._bot_task:
            self._bot_task.cancel()
            self._bot_task = None
            if self._bot and not self._bot.is_closed():
                await self._bot.close()
                self._bot = None

    async def stop(self):
        logger.info(f"Discord Service stop calling")
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
