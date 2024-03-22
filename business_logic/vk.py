import asyncio
import datetime
import logging
import random
from enum import StrEnum
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
    AttachmentType,
    Message,
    WallPost
)
from services.vk_bot.models.vk import WallItemFilter

logger = logging.getLogger(__name__)


class GroupPostMode(StrEnum):
    COMPILE_9 = 'compile_9'
    INSTANT = 'instant'


async def file_to_vk_attachment(
        client: VkClient,
        peer_id: int,
        file_path: str,
        t: AttachmentType
) -> str | None:
    match t:
        case AttachmentType.PHOTO:
            tmp = await client.upload.photos_message(
                peer_id,
                [file_path]
            )
            result = tmp[0] if tmp else None
        case AttachmentType.DOC:
            result = await client.upload.doc_message(
                peer_id,
                file_path
            )
        case _ as arg:
            logger.info(arg)
            result = None
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

        products = soup.find_all("li", {"class": "CbirMarketProducts-Item CbirMarketProducts-Item_type_product"})
        if products:
            for p in products:
                price = p.find('span', {"class": "Price-Value"}).get_text()
                link = p.find('a').get('href', None)
                if "http" not in link:
                    if "market.yandex" in link:
                        link = f"https:{link}"
                    elif "products/product" in link:
                        link = f"https://yandex.ru{link}"
                    else:
                        continue
                if price and link:
                    result.products_data.append(
                        f"{price} - {link}"
                    )

        if result.tags:
            break
        await asyncio.sleep(3)

    return result


async def post_in_group_wall(
        client: VkClient,
        message_text: str = '',
        attachments: list[str] | None = None,
        mode: GroupPostMode = GroupPostMode.COMPILE_9,
        notify: bool = True
):
    if not message_text and not attachments:
        return None

    post_model = WallPost(
        message_text=message_text,
        attachments=','.join(attachments)
    )
    if mode is GroupPostMode.COMPILE_9:
        posts = await client.wall.get(WallItemFilter.POSTPONED)
        available_posts = [
            p
            for p in posts
            if len(p.attachments) + len(attachments) <= 9 and p.post_source['type'] == 'api'
        ]
        if not available_posts:
            logger.info(f'Create new post {post_model} compile')
            await client.wall.post(
                post=post_model,
                post_time=randomize_time(datetime.datetime.now() + datetime.timedelta(days=2))
            )
        else:
            available_posts.sort(key=lambda x: len(x.attachments), reverse=True)
            post = available_posts[0]

            logger.info(f"Edit {post.id=} for {len(attachments)} new attachments. {post_model}")

            post_attachments = [
                                   a.photo.attachment_str
                                   for a in post.attachments if a.photo
                               ] + attachments
            post_model.attachments = ','.join(post_attachments)
            await client.wall.edit(
                post_id=post.id,
                post=post_model,
                post_time=randomize_time(
                    datetime.datetime.now() + datetime.timedelta(days=2 if len(post_attachments) >= 9 else 14)
                )
            )
            if len(post_attachments) >= 9:
                logger.info(f"{post.id=} ready to publish")
                if notify:
                    await client.messages.send(
                        peer_id=client.user_id,
                        message=Message(
                            text=f"{post.id=} ready to publish"
                        )
                    )
    elif mode is GroupPostMode.INSTANT:
        logger.info(f'Create new post {post_model} instant')
        await client.wall.post(
            post=post_model,
            post_time=randomize_time(datetime.datetime.now() + datetime.timedelta(days=2))
        )
    else:
        return None


def randomize_time(
        dt: datetime.datetime,
        delta: datetime.timedelta = datetime.timedelta(minutes=600)
) -> datetime.datetime:
    delta_seconds = int(delta.total_seconds())
    rand_seconds = random.randint(-delta_seconds, delta_seconds)
    return dt + datetime.timedelta(seconds=rand_seconds)
