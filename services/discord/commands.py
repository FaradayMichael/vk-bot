import logging
from pprint import pformat

import discord
from discord import (
    VoiceClient,
    Guild,
    ChannelType
)
from discord.ext.commands import Context

from services.discord.misc.yt import YTDLSource
from services.discord.service import DiscordService

logger = logging.getLogger(__name__)


async def test(ctx: Context):
    logger.info(pformat(vars(ctx)))
    await ctx.reply(content="test")


async def play(
        ctx: Context,
        url: str | None = None
):
    if url is None:
        return None

    bot = ctx.bot
    voice = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if not voice:
        voice = ctx.message.author.voice
        if not voice:
            logger.info(f"No voice client found for {ctx.message.author}")
            return None
        else:
            channel = ctx.message.author.voice.channel
            await channel.connect()

    voice_client: VoiceClient = ctx.message.guild.voice_client  # noqa
    if voice_client.is_playing():
        voice_client.stop()
    try:
        player = await YTDLSource.from_url(url, loop=ctx.bot.loop, stream=True)
        voice_client.play(player, after=lambda e: print('Player error: %s' % e) if e else None)
        logger.info(f"Now playing: {url}")
    except Exception as e:
        logger.exception(e)
        return None


async def stop(ctx: Context):
    voice_client: VoiceClient = ctx.message.guild.voice_client  # noqa
    if voice_client and voice_client.is_playing():
        logger.info(f"Stopped playing in {voice_client.channel}")
        voice_client.stop()
        try:
            await voice_client.disconnect()
        except Exception as e:
            logger.exception(e)


async def clown(ctx: Context, user_id: int | None = None):
    service: DiscordService = ctx.command.extras['service']
    if ctx.author.id != service.config.discord.main_user_id:
        return None
    if user_id is None:
        user_id = ctx.author.id

    for guild in ctx.bot.guilds:
        guild: Guild
        for channel in guild.channels:
            if channel.type is ChannelType.text:
                async for message in channel.history():
                    if message.author.id == user_id:
                        await message.add_reaction("🤡")
