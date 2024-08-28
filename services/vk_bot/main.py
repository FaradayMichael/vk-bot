import asyncio
import logging

from misc.config import Config
from services.vk_bot.service import VkBotService


def main(args, config: Config):
    logging.info(f'Creating VkBot Service')
    loop = asyncio.get_event_loop()

    service: VkBotService | None = None
    try:
        service = loop.run_until_complete(init(args, config=config, loop=loop))
        loop.run_forever()
    except Exception as exc:
        if service:
            service.close()
        logging.exception(exc)


async def init(args, config: Config, loop: asyncio.AbstractEventLoop):
    service = await VkBotService.create(config, loop)
    await service.start()
    return service
