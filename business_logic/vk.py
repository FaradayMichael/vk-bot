import asyncio
import logging
import uuid
from typing import assert_never
from urllib.parse import (
    urljoin,
    unquote,
    quote
)

import aiohttp
from bs4 import BeautifulSoup

from misc.vk_client import VkClient
from models.images import ImageTags
from models.vk import (
    AttachmentInput,
    AttachmentType
)

logger = logging.getLogger(__name__)


async def base64_to_vk_attachment(
        client: VkClient,
        peer_id: int,
        attachments: list[AttachmentInput]
) -> list[str]:
    result = []
    for a in attachments:
        file_path = f"static/{uuid.uuid4().hex}.{a.file.ext()}"
        with open(file_path, 'wb') as f:
            await asyncio.to_thread(
                f.write,
                a.file.data
            )
        match a.type:
            case AttachmentType.PHOTO:
                result += await client.upload_photos_message(
                    peer_id,
                    [file_path]
                )
            case AttachmentType.DOC:
                result.append(
                    await client.upload_doc_message(
                        peer_id,
                        file_path
                    )
                )
            case _ as arg:
                logger.info(arg)
                assert_never(arg)
    return result


async def parse_image_tags(
        image_link: str,
        tries: int = 3
) -> ImageTags:
    match_str = "https://yandex.ru/images/search?text="
    base_search_url = "https://yandex.ru/images/search?rpt=imageview&url="

    search_url = base_search_url + quote(image_link)
    logger.info(search_url)

    result = ImageTags()
    for i in range(tries):
        if i > 0:
            logger.info(f'try: {i + 1}')
        async with aiohttp.ClientSession() as session:
            async with session.get(search_url) as resp:
                if not resp.status == 200:
                    logger.info(await resp.text())
                    await asyncio.sleep(5)
                    continue
                soup = BeautifulSoup(await resp.read(), features="html5lib")
        await asyncio.sleep(0)

        links = soup('a')
        if "captcha" in " ".join(str(x) for x in links):
            logger.info("Captcha!")
            await asyncio.sleep(5)
            continue

        for link in links:
            if 'href' in dict(link.attrs):
                url = urljoin(search_url, link['href'])
                if url.find("'") != -1:
                    continue
                url = url.split('#')[0]
                if match_str in url:
                    result.tags.append(
                        unquote(url.replace(match_str, ''))
                    )

        desc = soup.find('div', {"class": "CbirObjectResponse-Description"})
        if desc:
            result.description = desc.text

        if result.tags:
            break
        await asyncio.sleep(3)

    return result
