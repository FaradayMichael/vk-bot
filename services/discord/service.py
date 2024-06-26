import asyncio
import logging

from asyncpg import Pool
from discord import (
    Intents,
    Message,
    File
)
from discord.ext.commands import Bot
from discord.ext.commands.core import Command
from redis.asyncio import Redis

from db import (
    reply_commands as reply_commands_db
)
from misc import (
    db,
    redis
)
from misc.config import Config
from misc.gigachat_client import GigachatClient

# https://discordpy.readthedocs.io/en/stable/api.html

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

        self.gigachat_client: GigachatClient | None = None

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
        self.gigachat_client = GigachatClient(self.config.gigachat)

        self._intents = Intents.all()
        self._intents.messages = True
        self._bot = Bot(command_prefix="/", intents=self._intents)
        await self._register_commands()
        self._register_events()

    async def start(self):
        logger.info("Starting Discord Service")
        self.stopping = False
        await self.start_bot()
        self._start_schedule_tasks()

    async def start_bot(self) -> None:
        if self._bot:
            self._bot_task = self.loop.create_task(self.run_bot(self._bot))
        while not self._bot.is_ready():
            logger.info("Waiting for Bot ready...")
            await asyncio.sleep(1)
        logger.info(f"Started Discord Bot {self._bot.user.id}")

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
        from .scheduled import (
            send_on_schedule,
            drop_broken_activities,
            cb_task
        )
        self._tasks.append(
            self.loop.create_task(
                send_on_schedule(
                    self,
                    "0 9 * * 2",
                    937785108696551546,
                    filepaths=["static/test.gif"]
                )
            )
        )
        self._tasks.append(
            self.loop.create_task(
                drop_broken_activities(
                    self,
                    "0 0 * * *"
                )
            )
        )
        self._tasks.append(
            self.loop.create_task(
                cb_task(
                    self,
                    "0 10 * * *",
                    937785108696551546
                )
            )
        )

    # noinspection PyTypeChecker
    async def _register_commands(self) -> None:
        command_names = [
            'test',
            'play',
            'stop',
            'clown',
            'boris'
        ]
        reply_commands = await reply_commands_db.get_all(self.db_pool)

        from . import commands
        commands_map = {
            c: getattr(commands, c)
            for c in command_names
        } | {
            r_c.command: commands.reply
            for r_c in reply_commands
        }

        for command_name, call in commands_map.items():
            command = Command(call, name=command_name, extras={'service': self})
            self._bot.add_command(command)

    def _register_events(self) -> None:
        from . import events

        async def on_message(message: Message):
            return await events.on_message(self, message)

        async def on_voice_state_update(member, before, after):
            return await events.on_voice_state_update(self, member, before, after)

        async def on_presence_update(before, after):
            return await events.on_presence_update(self, before, after)

        self._bot.event(events.on_ready)
        self._bot.event(on_message)
        self._bot.event(on_presence_update)
        self._bot.event(on_voice_state_update)

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
        if self.gigachat_client:
            await self.gigachat_client.close()
            self.gigachat_client = None
