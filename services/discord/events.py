import logging

from discord.member import Member

logger = logging.getLogger(__name__)


async def on_ready():
    logger.info('Ready')


async def on_presence_update(before: Member, after: Member):
    logger.info(before.activities)
    logger.info(before.status)

    logger.info(after.activities)
    logger.info(after.status)
