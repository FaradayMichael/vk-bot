import asyncio
import datetime
import logging

import croniter
from discord import File
from discord.ext.commands import Bot

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
            now = datetime.datetime.now()
            nxt: datetime.datetime = croniter.croniter(cron, now).get_next(datetime.datetime)
            sleep = (nxt - now).total_seconds()
            logger.info(f"Schedule {sleep=} {channel=}")
            await asyncio.sleep(sleep)

            files = [
                File(fp) for fp in filepaths
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
