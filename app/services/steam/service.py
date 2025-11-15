import asyncio
import datetime
import logging

from redis.asyncio import Redis
from urllib3.exceptions import NameResolutionError

from app.db import (
    steam as steam_db
)
from app.models import SteamUser, SteamActivitySession
from app.utils.db import (
    DBHelper,
    init_db
)
from app.utils import redis
from app.utils.config import Config
from app.utils.service import BaseService
from app.services.steam.client import SteamClient

logger = logging.getLogger(__name__)


class SteamService(BaseService):
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
        self._tasks: list[asyncio.Task] = []

        self.steam_client: SteamClient = SteamClient(self.loop, config.steam.key)
        self.process_users = config.steam.user_ids

    async def _process_users_task(self):
        while not self.stopping:
            try:
                async with self.db_helper.get_session() as session:
                    users_db = await steam_db.get_users(session)
                    users_db_map = {i.steam_id: i for i in users_db}
                    for user_steam_id in self.process_users:
                        steam_data = await self.steam_client.get_user_details(user_steam_id)
                        if not steam_data:
                            logger.error(f"Steam user {user_steam_id} not found")
                            continue
                        activity = steam_data.get("gameextrainfo")
                        username = steam_data.get("personaname")

                        user_db = users_db_map.get(user_steam_id)
                        if not user_db:
                            logger.info(f"Steam user {username} {user_steam_id} not exist in DB")
                            user_db = SteamUser(
                                steam_id=user_steam_id,
                                username=username,
                            )
                            session.add(user_db)
                            await session.commit()

                        if user_db.username != username:
                            user_db.username = username

                        current_activity_db = await steam_db.get_current_activity(session, user_db.id)
                        current_activity = current_activity_db.activity_name if current_activity_db else None
                        if current_activity != activity:
                            if current_activity is not None:
                                # Finish activity
                                logger.info(f"Steam user {username} {user_steam_id} finish activity {current_activity}")
                                current_activity_db.finished_at = datetime.datetime.now(datetime.UTC).replace(tzinfo=None)

                            if activity is not None:
                                # Start new activity
                                logger.info(f"Steam user {username} {user_steam_id} start activity {activity}")
                                new_activity_db = SteamActivitySession(
                                    user_id=user_db.id,
                                    steam_id=user_steam_id,
                                    activity_name=activity,
                                    extra_data={"username": username},
                                )
                                session.add(new_activity_db)

                            await session.commit()
                            await asyncio.sleep(3)

            except (asyncio.CancelledError, StopIteration, GeneratorExit, KeyboardInterrupt):
                return await self.stop()
            except NameResolutionError as e:
                logger.exception(e)
                await asyncio.sleep(120)
            except Exception as e:
                logger.exception(e)
            await asyncio.sleep(60)

    @classmethod
    async def create(
            cls,
            config: Config,
            loop: asyncio.AbstractEventLoop,
            **kwargs
    ) -> "SteamService":
        return await super().create(config, 'steam_service', loop, **kwargs)  # noqa

    async def init(self):
        self.db_helper = await init_db(self.config.db)
        self.redis_conn = await redis.init(self.config.redis)

    async def start(self):
        self._tasks.append(asyncio.create_task(self._process_users_task()))

    async def close(self):
        for task in self._tasks:
            try:
                task.cancel()
                await task
            except Exception as e:
                logger.error(e)

        if self.db_helper:
            await self.db_helper.close()
            self.db_helper = None
        if self.redis_conn:
            await redis.close(self.redis_conn)
            self.redis_conn = None
