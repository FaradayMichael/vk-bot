import asyncio
import datetime
import logging
from typing import Any

import croniter
import discord
from discord.ext.commands import Bot

from app.db import activity_sessions as activity_sessions_db, status_sessions as status_sessions_db
from .models.activities import StatusSession
from .service import DiscordService

logger = logging.getLogger(__name__)


async def send_on_schedule(
        service: DiscordService,
        cron: str,
        channel_id: int,
        content: str | None = None,
        filepaths: list[str] | None = None,
        **kwargs
):
    bot: Bot = service.bot
    channel = bot.get_channel(channel_id)
    while not service.stopping:
        try:
            sleep = _get_sleep_seconds(cron)
            logger.info(f"Schedule send {sleep=} {channel=}")
            await asyncio.sleep(sleep)

            files = [
                discord.File(fp) for fp in filepaths
            ] if filepaths else None
            await channel.send(
                content=content,
                files=files,
                **kwargs
            )

        except (GeneratorExit, asyncio.CancelledError, KeyboardInterrupt):
            break
        except Exception as e:
            logger.exception(e)
            await asyncio.sleep(300)


async def drop_broken_activities(
        service: DiscordService,
        cron: str,
        timeout_hours: int = 48,
) -> None:
    while not service.stopping:
        try:
            sleep = _get_sleep_seconds(cron)
            logger.info(f"Schedule drop activities {sleep=}")
            await asyncio.sleep(sleep)

            now = datetime.datetime.now(tz=datetime.timezone.utc)
            async with service.db_helper.get_session() as session:
                activities = await activity_sessions_db.get_list(session, unfinished=True)
                for activity in activities:
                    if (now - activity.started_at).total_seconds() / 3600 >= timeout_hours:
                        logger.info(f"Drop activity from db: {activity}")
                        await activity_sessions_db.delete(session, activity.id)

        except (GeneratorExit, asyncio.CancelledError, KeyboardInterrupt):
            break
        except Exception as e:
            logger.exception(e)
            await asyncio.sleep(300)


async def drop_broken_status_sessions(
        service: DiscordService,
        cron: str,
) -> None:
    while not service.stopping:
        try:
            sleep = _get_sleep_seconds(cron)
            logger.info(f"Schedule drop discord sessions {sleep=}")
            await asyncio.sleep(sleep)

            async with service.db_helper.get_session() as session:
                sessions = await status_sessions_db.get_list(session, unfinished=True)

                sessions_map: dict[Any, list] = {}
                for session_db in sessions:
                    if sessions_map.get(session_db.user_id):
                        sessions_map[session_db.user_id].append(session_db)
                    else:
                        sessions_map[session_db.user_id] = [session_db]

                to_delete: list[StatusSession] = []
                for sessions in sessions_map.values():
                    if len(sessions) > 1:
                        sessions.sort(key=lambda x: x.started_at)
                        to_delete += sessions[:-1]

                for i in to_delete:
                    await status_sessions_db.delete(session, i.id)

        except (GeneratorExit, asyncio.CancelledError, KeyboardInterrupt):
            break
        except Exception as e:
            logger.exception(e)
            await asyncio.sleep(300)


def _get_sleep_seconds(
        cron: str,
) -> float:
    now = datetime.datetime.now()
    nxt: datetime.datetime = croniter.croniter(cron, now).get_next(datetime.datetime)
    return (nxt - now).total_seconds()
