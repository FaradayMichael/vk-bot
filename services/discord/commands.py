import logging
from pprint import pformat

from discord import (
    VoiceClient,
    Guild,
    ChannelType
)
from discord.ext.commands import Context

from db import (
    reply_commands as reply_commands_db
)
from .utils.voice_channels import (
    connect_to_voice_channel,
    play_yt_url,
    play_file
)
from .service import (
    DiscordService
)

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
    if not ctx.message.author.voice:
        return None

    await connect_to_voice_channel(bot, ctx.message.author.voice.channel)

    voice_client: VoiceClient | None = ctx.voice_client
    if voice_client.is_playing():
        voice_client.stop()
    try:
        await play_yt_url(voice_client, url)
        logger.info(f"Now playing: {url}")
    except Exception as e:
        logger.exception(e)
        return None


async def stop(ctx: Context):
    voice_client: VoiceClient | None = ctx.voice_client
    if voice_client and voice_client.is_playing():
        logger.info(f"Stopped playing in {voice_client.channel}")
        voice_client.stop()
        try:
            await voice_client.disconnect()
        except Exception as e:
            logger.exception(e)


async def clown(ctx: Context, user_id: int | None = None):
    service: DiscordService = ctx.command.extras['service']

    if user_id == service.config.discord.main_user_id:
        return None

    for guild in ctx.bot.guilds:
        guild: Guild
        for channel in guild.channels:
            if channel.type is ChannelType.text:
                async for message in channel.history():
                    if message.author.id == user_id:
                        await message.add_reaction("🤡")


async def boris(ctx: Context):
    voice_client: VoiceClient | None = ctx.voice_client
    if voice_client:
        await connect_to_voice_channel(ctx.bot, voice_client.channel)
        try:
            await play_file(voice_client, 'static/boris.mp4')
        except Exception as e:
            logger.exception(e)


async def reply(ctx: Context):
    service: DiscordService = ctx.command.extras['service']
    command_db = await reply_commands_db.get(
        service.db_pool,
        ctx.command.name
    )
    if command_db:
        if command_db.reply:
            await ctx.reply(command_db.text)
        else:
            if command_db.channel_id:
                channel = service.bot.get_channel(command_db.channel_id)
                if channel:
                    await channel.send(command_db.text)
                else:
                    logger.error(f"Channel {command_db.channel_id} not found")
            else:
                await ctx.send(command_db.text)
