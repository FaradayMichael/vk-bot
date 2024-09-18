import asyncio
import logging

from misc.config import Config
from services.db_dumper.service import DumperService

logger = logging.getLogger(__name__)


def main(args, config: Config):
    logger.info("Starting DB Dumper Service")
    loop = asyncio.get_event_loop()

    service: DumperService | None = None
    try:
        service = loop.run_until_complete(init(args, config=config, loop=loop))
        loop.run_forever()
    except Exception as exc:
        if service:
            service.close()
        logging.exception(exc)


async def init(args, config: Config, loop: asyncio.AbstractEventLoop):
    service = DumperService(loop, config)
    return service
