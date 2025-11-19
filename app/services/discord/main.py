import asyncio
import logging

from app.utils.config import Config
from .service import DiscordService


def main(args, config: Config):
    logging.info(f"Creating Discord Service")
    loop = asyncio.get_event_loop()

    service: DiscordService | None = None
    try:
        service = loop.run_until_complete(init(args, config=config, loop=loop))
        loop.run_forever()
    except Exception as exc:
        if service:
            service.close()
        logging.exception(exc)


async def init(args, config: Config, loop: asyncio.AbstractEventLoop):
    service = await DiscordService.create(config, loop)
    await service.start()
    return service
