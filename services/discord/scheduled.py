import asyncio
import datetime
import logging
import os

import croniter
import discord
from discord.ext.commands import Bot

from db import (
    activity_sessions as activity_sessions_db,
    dynamic_config as dynamic_config_db
)
from business_logic import (
    images as images_bl
)
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
            async with service.db_pool.acquire() as conn:
                activities = await activity_sessions_db.get_all(conn, unfinished=True)
                for activity in activities:
                    if (now - activity.started_at).total_seconds() / 3600 >= timeout_hours:
                        logger.info(f"Drop activity from db: {activity}")
                        await activity_sessions_db.delete(conn, activity.id)

        except (GeneratorExit, asyncio.CancelledError, KeyboardInterrupt):
            break
        except Exception as e:
            logger.exception(e)
            await asyncio.sleep(300)


async def cb_task(
        service: DiscordService,
        cron: str,
        channel_id: int
) -> None:
    while not service.stopping:
        try:
            sleep = _get_sleep_seconds(cron)
            logger.info(f"Schedule cb {sleep=}")
            await asyncio.sleep(sleep)

            dynamic_conf = await dynamic_config_db.get(service.db_pool)
            image_text = dynamic_conf['cb2']['image_message'].format(count=dynamic_conf['cb2']['counter'])

            filename = images_bl.add_text_to_image(
                filepath='templates/template_1.jpg',
                text=image_text,
                font="templates/Impact.ttf",
                font_size=48,
                text_xy_rel=(0.5, 0.9)
            )

            channel = service.bot.get_channel(channel_id)
            await channel.send(
                content=f"<@292615364448223233> {dynamic_conf['cb2']['message']}", file=discord.File(filename)
            )

            try:
                os.remove(filename)
            except Exception as e:
                logger.error(e)

            dynamic_conf['cb2']['counter'] += 1
            await dynamic_config_db.update(service.db_pool, dynamic_conf)
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
