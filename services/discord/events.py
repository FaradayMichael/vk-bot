import logging

from discord import (
    Message,
    VoiceClient
)
from discord.member import (
    Member,
    VoiceState
)

from business_logic.images import parse_image_tags
from models.base import AttachmentType
from models.images import ImageTags
from .service import DiscordService

logger = logging.getLogger(__name__)

DISCORD_MEDIA_PREFIX = 'https://media'
IMG_EXT = ('jpg', 'jpeg', 'png', 'gif', 'bmp')


# https://discordpy.readthedocs.io/en/stable/api.html?highlight=event#event-reference

async def on_message(service: DiscordService, message: Message):
    if message.author.bot:
        return None

    await service.bot.process_commands(message)
    log_message(message)

    image_urls = _get_image_urls_from_text(message.content)

    if message.attachments:
        logger.info(message.attachments)
        for attachment in message.attachments:
            if AttachmentType.by_content_type(attachment.content_type) is AttachmentType.PHOTO:
                image_urls.append(attachment.url)

    if image_urls:
        result_tags: list[ImageTags] = []
        for image_url in image_urls:
            tags = await parse_image_tags(image_url)
            if tags and (tags.tags or tags.description):
                result_tags.append(tags)
        logger.info(f"{result_tags=}")
        if result_tags:
            await message.reply(
                content='\n\n'.join(
                    [f"{i + 1}. {m.text()}" for i, m in enumerate(result_tags)]
                )
            )


async def on_ready():
    logger.info('Ready')


async def on_presence_update(before: Member, after: Member):
    pass
    # logger.info(before.activities)
    # logger.info(before.status)
    #
    # logger.info(after.activities)
    # logger.info(after.status)


async def on_voice_state_update(
        service: DiscordService,
        member: Member,
        before: VoiceState,
        after: VoiceState
):
    async def on_leave_channel():
        channel = before.channel
        logger.info(f"Member {member.display_name} has left the voice channel {channel.name}")
        logger.info(bot.voice_clients)
        for v_c in bot.voice_clients:
            v_c: VoiceClient
            if v_c.channel.id == channel.id and len(v_c.channel.members) == 1:
                await v_c.disconnect()

    async def on_join_channel():
        channel = after.channel
        logger.info(f"Member {member.display_name} joined voice channel {channel.name}")

    async def on_move():
        from_channel = before.channel
        to_channel = after.channel
        logger.info(f"Member {member.display_name} moved from {from_channel.name} to {to_channel.name}")

    bot = service.bot
    if before.channel and after.channel:
        if before.channel.id == after.channel.id:
            return None
        await on_move()
    else:
        if before.channel:
            await on_leave_channel()
        if after.channel:
            await on_join_channel()
    return None


def log_message(message: Message):
    logger.info(f"{message.author=}")
    logger.info(f"{message.content=}")
    logger.info(f"{message.attachments=}")
    logger.info(f"{message.stickers=}")


def _get_image_urls_from_text(text: str) -> list[str]:
    if not text:
        return []

    urls = []
    words = text.split()
    for word in words:
        if word.startswith(DISCORD_MEDIA_PREFIX):
            if any(ext in word for ext in IMG_EXT):
                urls.append(word)
    return urls
