import asyncio
import datetime
import logging
import os
import uuid
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
    AttachmentInput,
    AttachmentType,
    WallPost,
    Message
)
from services.vk_bot.models import WallItemFilter

logger = logging.getLogger(__name__)


class GroupPostMode(StrEnum):
    COMPILE_9 = 'compile_post'
    INSTANT = 'instant'


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
        r = await file_to_vk_attachment(client, peer_id, file_path, a.type)
        if r:
            result.append(r)

        try:
            os.remove(file_path)
        except FileNotFoundError:
            pass

    return result


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
                post_time=datetime.datetime.now() + datetime.timedelta(days=2)
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
                post_time=datetime.datetime.now() + datetime.timedelta(days=2 if len(post_attachments) >= 9 else 14)
            )
            if len(post_attachments) >= 9:
                logger.info(f"{post.id=} ready to publish")
                if notify:
                    await client.messages.send(
                        peer_id=client.config.vk.main_user_id,
                        message=Message(
                            text=f"{post.id=} ready to publish"
                        )
                    )
    elif mode is GroupPostMode.INSTANT:
        logger.info(f'Create new post {post_model} instant')
        await client.wall.post(
            post=post_model,
            post_time=datetime.datetime.now() + datetime.timedelta(days=2)
        )
    else:
        return None
