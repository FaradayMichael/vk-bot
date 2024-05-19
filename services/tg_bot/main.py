import asyncio
import logging

from aiogram import (
    Bot,
    Dispatcher,
)

from misc.config import Config

logger = logging.getLogger(__name__)


async def main(args, config: Config):
    logger.info("Creating Tg bot")
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(init(args, config, loop))
        loop.run_forever()
    except Exception as e:
        logger.exception(e)


async def init(args, config: Config, loop: asyncio.AbstractEventLoop):
    bot = Bot(token=config.tg.token)
    dp = Dispatcher()

    await dp.start_polling(bot)


