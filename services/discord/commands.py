import logging
from pprint import pformat

import discord
from discord import VoiceClient
from discord.ext.commands import command, Context

from services.discord.misc.yt import YTDLSource

logger = logging.getLogger(__name__)


@command(name="test")
async def test(ctx: Context):
    logger.info(pformat(vars(ctx)))
    await ctx.reply(content="test")


@command(name="play")
async def play(
        ctx: Context,
        url: str | None = None
):
    if url is None:
        return None

    logger.info(repr(ctx.message.author.voice))

    # test_id = 1241728108768264216
    # channel = discord.utils.get(ctx.bot.get_all_channels(), id=test_id)

    voice = ctx.message.author.voice
    if voice is None:
        return None
    channel = voice.channel
    logger.info(repr(channel))
    voice_client: VoiceClient = await channel.connect(reconnect=False)
    try:
        player = await YTDLSource.from_url(url, loop=ctx.bot.loop, stream=True)
        voice_client.play(player, after=lambda e: print('Player error: %s' % e) if e else None)
    except Exception as e:
        logger.exception(e)
        return None
