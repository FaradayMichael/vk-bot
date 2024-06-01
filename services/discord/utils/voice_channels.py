import logging

from discord import (
    VoiceChannel,
    utils,
    VoiceClient,
    FFmpegPCMAudio,
    AudioSource
)
from discord.ext.commands import Bot

from .yt import YTDLSource

logger = logging.getLogger(__name__)


async def connect_to_voice_channel(bot: Bot, voice_channel: VoiceChannel) -> VoiceClient:
    voice_client = utils.get(bot.voice_clients, channel=voice_channel)
    if not voice_client:
        voice_client = await voice_channel.connect()
    return voice_client


async def leave_from_empty_voice_channel(bot: Bot):
    for v_c in bot.voice_clients:
        v_c: VoiceClient
        channel = v_c.channel
        members = channel.members
        bots_members = list(filter(lambda m: m.bot, members))
        if len(members) == len(bots_members):
            await v_c.disconnect()


async def play_file(voice_client: VoiceClient, filepath: str):
    try:
        source = FFmpegPCMAudio(source=filepath)
        await play_in_voice(voice_client, source)
    except Exception as e:
        logger.error(e)


async def play_yt_url(voice_client: VoiceClient, url: str, stream: bool = True):
    try:
        source = await YTDLSource.from_url(url, stream=stream)
        await play_in_voice(voice_client, source)
    except Exception as e:
        logger.error(e)


async def play_in_voice(voice_client: VoiceClient, source: AudioSource):
    if voice_client.is_playing():
        voice_client.stop()
    try:
        voice_client.play(source)
    except Exception as e:
        logger.error(e)
