import asyncio
import logging

from misc.config import Config
from .service import ParserService


def main(args, config: Config):
    logging.info(f'Creating Parser Service')
    loop = asyncio.get_event_loop()

    service: ParserService | None = None
    try:
        service = loop.run_until_complete(init(args, config=config, loop=loop))
        loop.run_forever()
    except Exception as exc:
        if service:
            service.close()
        logging.exception(exc)


async def init(args, config: Config, loop: asyncio.AbstractEventLoop):
    service = await ParserService.create(config, loop)
    return service
