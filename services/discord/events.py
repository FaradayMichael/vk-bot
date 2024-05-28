import logging

from discord import (
    Message,
    VoiceClient,
    ActivityType
)
from discord.ext.commands import Bot
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

    log_message(message)

    if message.author.id in (292615364448223233,):
        await message.add_reaction("🤡")

    await service.bot.process_commands(message)

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
    before_playing_activities = sorted(
        [a.name for a in before.activities if a.type is ActivityType.playing],
    )
    after_playing_activities = sorted(
        [a.name for a in after.activities if a.type is ActivityType.playing]
    )
    before_playing_activities = set(before_playing_activities)
    after_playing_activities = set(after_playing_activities)
    if before_playing_activities != after_playing_activities:
        if len(before_playing_activities) > len(after_playing_activities):
            pass
        elif len(before_playing_activities) < len(after_playing_activities):
            new_activities = after_playing_activities - before_playing_activities
            logger.info(f"{before.name} start playing {new_activities}")
        else:
            pass


async def on_voice_state_update(
        service: DiscordService,
        member: Member,
        before: VoiceState,
        after: VoiceState
):
    async def on_leave_channel():
        channel = before.channel
        logger.info(f"Member {member.display_name} has left the voice channel {channel.name}")

    async def on_join_channel():
        channel = after.channel
        logger.info(f"Member {member.display_name} joined voice channel {channel.name}")

    async def on_move():
        from_channel = before.channel
        to_channel = after.channel
        logger.info(f"Member {member.display_name} moved from {from_channel.name} to {to_channel.name}")

    async def on_start_stream():
        channel = after.channel
        logger.info(f"Member {member.display_name} started streaming in {channel.name}")

    bot = service.bot
    await leave_from_empty_channel(bot)
    if before.channel and after.channel:
        if before.channel.id == after.channel.id:
            if not before.self_stream and after.self_stream:
                await on_start_stream()
            return None
        await on_move()
    else:
        if before.channel:
            await on_leave_channel()
        if after.channel:
            await on_join_channel()
    return None


async def leave_from_empty_channel(bot: Bot):
    for v_c in bot.voice_clients:
        v_c: VoiceClient
        channel = v_c.channel
        members = channel.members
        bots_members = list(filter(lambda m: m.bot, members))
        if len(members) == len(bots_members):
            await v_c.disconnect()


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
