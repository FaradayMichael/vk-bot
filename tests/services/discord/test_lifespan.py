import asyncio

import pytest

from misc.config import Config
from services.discord.service import DiscordService


@pytest.mark.asyncio
async def test_discord_service(
        conf: Config,
        #event_loop
):
    loop = asyncio.get_event_loop()
    service = await DiscordService.create(loop, conf)
    await service.start()
    await asyncio.sleep(5)
    await service.close()
