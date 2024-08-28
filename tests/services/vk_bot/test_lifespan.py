import asyncio

import pytest

from misc.config import Config
from misc.vk_client import VkClient
from services.vk_bot.service import VkBotService


@pytest.mark.asyncio
async def test_vk_client(conf: Config):
    client = VkClient(conf.vk)
    await asyncio.sleep(5)
    await client.close()


@pytest.mark.asyncio
async def test_vk_service(conf: Config, event_loop):
    loop = asyncio.get_event_loop()
    service = await VkBotService.create(conf, loop)
    await service.start()
    await asyncio.sleep(15)
    service.stop()
