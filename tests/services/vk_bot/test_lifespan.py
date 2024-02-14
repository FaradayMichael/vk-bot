import asyncio

import pytest

from misc.config import Config
from misc.vk_client import VkClient
from services.vk_bot.service import VkBotService


@pytest.mark.asyncio
async def test_vk_client(conf: Config):
    client = VkClient(conf)
    await asyncio.sleep(5)
    await client.close()


@pytest.mark.asyncio
async def test_vk_service(conf: Config, event_loop):
    service = await VkBotService.create(event_loop, conf)
    await service.start()
    await asyncio.sleep(10)
    service.stop()
