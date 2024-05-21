import logging
from pprint import pformat

from discord.ext.commands import command, Context

logger = logging.getLogger(__name__)


@command(name="test")
async def test(ctx: Context):
    logger.info(pformat(vars(ctx)))
    await ctx.reply(content="test")
