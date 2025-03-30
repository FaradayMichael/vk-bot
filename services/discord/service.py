import asyncio
import logging

from discord import (
    Intents,
    Message,
)
from discord.ext.commands import Bot
from discord.ext.commands.core import Command
from redis.asyncio import Redis

from db import (
    reply_commands as reply_commands_db
)
from services.utils.client import UtilsClient
from services.vk_bot.client import VkBotClient
from utils.db import (
    DBHelper,
    init_db
)
from utils import redis
from utils.config import Config
from utils.service import BaseService

# https://discordpy.readthedocs.io/en/stable/api.html

logger = logging.getLogger(__name__)


class DiscordService(BaseService):
    def __init__(
            self,
            config: Config,
            controller_name: str,
            loop: asyncio.AbstractEventLoop,
            **kwargs
    ):
        super().__init__(config, controller_name, loop, **kwargs)

        self.db_helper: DBHelper | None = None
        self.redis_conn: Redis | None = None

        self.vk_pot_client: VkBotClient | None = None
        self.utils_client: UtilsClient | None = None

        self._intents: Intents | None = None
        self._bot: Bot | None = None
        self._bot_task: asyncio.Task | None = None

        self._service_channel_id: int = 937785155727294474
        self._tasks: list[asyncio.Task] = []

    @classmethod
    async def create(
            cls,
            config: Config,
            loop: asyncio.AbstractEventLoop,
            **kwargs
    ) -> "DiscordService":
        return await super().create(config, 'discord_service', loop, **kwargs)  # noqa

    async def init(self):
        self.db_helper = await init_db(self.config.db)
        self.redis_conn = await redis.init(self.config.redis)

        self.vk_pot_client = await VkBotClient.create(self.amqp)
        self.utils_client = await UtilsClient.create(self.amqp)

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
            await asyncio.sleep(30)
        logger.info(f"Started Discord Bot {self._bot.user.id}")

    async def run_bot(self, bot: Bot) -> None:
        logger.info(f"Run Discord Bot")
        try:
            await bot.start(self.config.discord.token)
        except (GeneratorExit, asyncio.CancelledError, StopIteration):
            self.stop()
        except Exception as e:
            logger.error(e)
            return

    def _start_schedule_tasks(self) -> None:
        from .scheduled import (
            send_on_schedule,
            drop_broken_activities,
            drop_broken_status_sessions
            # cb_task
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
                drop_broken_status_sessions(
                    self,
                    "0 0 * * *",
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
            'boris',
            #'clear_history',
            'set_avatar',
        ]
        async with self.db_helper.get_session() as session:
            reply_commands = await reply_commands_db.get_list(session)

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

        # async def on_raw_reaction_add(payload):
        #     return await events.on_raw_reaction_add(self, payload)

        async def on_voice_state_update(member, before, after):
            return await events.on_voice_state_update(self, member, before, after)

        async def on_presence_update(before, after):
            return await events.on_presence_update(self, before, after)

        async def on_ready():
            return await events.on_ready(self)

        self._bot.event(on_message)
        # self._bot.event(on_raw_reaction_add)
        self._bot.event(on_presence_update)
        self._bot.event(on_voice_state_update)
        self._bot.event(on_ready)

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

    async def close(self):
        for task in self._tasks:
            task.cancel()
        self._tasks.tasks = []

        await self.stop_bot()

        if self.db_helper:
            await self.db_helper.close()
            self.db_helper = None
        if self.redis_conn:
            await redis.close(self.redis_conn)
            self.redis_conn = None

        if self.vk_pot_client:
            await self.vk_pot_client.close()
            self.vk_pot_client = None
        if self.utils_client:
            await self.utils_client.close()
            self.utils_client = None

        await super().close()
