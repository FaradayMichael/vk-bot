import asyncio
import logging

from utils.config import Config
from .service import UtilsService


def main(args, config: Config):
    logging.info(f'Creating Utils Service')
    loop = asyncio.get_event_loop()

    service: UtilsService | None = None
    try:
        service = loop.run_until_complete(init(args, config=config, loop=loop))
        loop.run_forever()
    except Exception as exc:
        if service:
            service.close()
        logging.exception(exc)


async def init(args, config: Config, loop: asyncio.AbstractEventLoop):
    service = await UtilsService.create(config, loop)
    return service
