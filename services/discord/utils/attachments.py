import logging

from discord.ext.commands import Bot
from discord.http import Route

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
