import logging
from typing import Sequence

from discord import Message
from discord.ext.commands import Bot
from discord.http import Route

from app.schemas.base import AttachmentType
from app.services.discord.consts import (
    VIDEO_EXT,
    IMG_EXT,
    DISCORD_MEDIA_PREFIX,
    DISCORD_ATTACHMENT_PREFIX,
)

logger = logging.getLogger(__name__)


async def refresh_attachments_urls(
        bot: Bot,
        urls: list[str]
) -> list[str]:
    if not urls:
        return []
    response: dict = await bot.http.request(
        route=Route(
            'POST',
            '/attachments/refresh-urls',
        ),
        json={
            "attachment_urls": urls
        }
    )
    if response and 'refreshed_urls' in response:
        return [
            i['refreshed']
            for i in response['refreshed_urls']
        ]
    logger.error(f'Failed to refresh attachments urls: {response}')
    return []


def get_video_attachment_urls_from_message(
        message: Message
) -> list[str]:
    video_urls = get_discord_urls_from_text(message.content, VIDEO_EXT)
    if message.attachments:
        for attachment in message.attachments:
            if AttachmentType.by_content_type(attachment.content_type) is AttachmentType.VIDEO:
                video_urls.append(attachment.url)
    return video_urls


def get_image_attachment_urls_from_message(
        message: Message
) -> list[str]:
    image_urls = get_discord_urls_from_text(message.content)
    if message.attachments:
        for attachment in message.attachments:
            if AttachmentType.by_content_type(attachment.content_type) is AttachmentType.PHOTO:
                image_urls.append(attachment.url)
    return image_urls


def get_yt_urls_from_message(
        message: Message
) -> list[str]:
    if not message.content:
        return []

    urls = []
    words = message.content.split()
    for word in words:
        if 'youtube.com/' in word:
            urls.append(word)
    return urls


def get_discord_urls_from_text(text: str, patterns_set: Sequence = IMG_EXT) -> list[str]:
    if not text:
        return []

    urls = []
    words = text.split()
    for word in words:
        if word.startswith(DISCORD_MEDIA_PREFIX) or word.startswith(DISCORD_ATTACHMENT_PREFIX):
            if any(p in word.lower() for p in patterns_set):
                urls.append(word)
    return urls
