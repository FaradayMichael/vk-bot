import datetime
import logging
import os
import random
from enum import StrEnum

from yt_dlp.utils import DownloadError

from business_logic.yt import (
    download_video as download_video_yt,
    reformat_short,
)
from utils.vk_client import VkClient
from schemas.vk import (
    Message,
    WallPost
)
from models_old.base import AttachmentType
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
    match mode:
        case GroupPostMode.COMPILE_9:
            posts = await client.wall.get(WallItemFilter.POSTPONED)
            available_posts = [
                p for p in posts
                if len(p.attachments) + len(attachments) <= 9 and p.post_source['type'] == 'api'
            ]
            if not available_posts:
                logger.info(f'Create new post {post_model} compile')
                await client.wall.post(
                    post=post_model,
                    post_time=_randomize_time(datetime.datetime.now() + datetime.timedelta(days=2))
                )
            else:
                available_posts.sort(key=lambda x: len(x.attachments), reverse=True)
                post = available_posts[0]

                logger.info(f"Edit {post.id=} for {len(attachments)} new attachments. {post_model}")

                post_attachments = [
                                       a.photo.attachment_str for a in post.attachments
                                       if a.photo
                                   ] + attachments
                post_model.attachments = ','.join(post_attachments)
                await client.wall.edit(
                    post_id=post.id,
                    post=post_model,
                    post_time=_randomize_time(
                        datetime.datetime.now() + datetime.timedelta(days=2 if len(post_attachments) >= 9 else 14)
                    )
                )
                if len(post_attachments) >= 9:
                    msg = f"{post.id=} ready to publish"
                    logger.info(msg)
                    if notify:
                        await client.messages.send(
                            peer_id=client.user_id,
                            message=Message(
                                text=msg
                            )
                        )

        case GroupPostMode.INSTANT:
            logger.info(f'Create new post {post_model} instant')
            await client.wall.post(
                post=post_model,
                post_time=_randomize_time(datetime.datetime.now() + datetime.timedelta(days=2))
            )

        case _ as arg:
            logger.error(f"Unsupported post mode: {arg}")
            return None


async def post_yt_video(
        client: VkClient,
        url: str,
):
    url = reformat_short(url)
    try:
        fp = await download_video_yt(url)
        if not fp:
            logger.error(f'Failed to download {url}')
            return None
        await client.upload.video_wall_and_post(fp)
        os.remove(fp)
    except DownloadError:
        await client.upload.video_wall_and_post(link=url)


async def download_video(
        attachment: str, # video-{owner_id}_{media_id}
        folder: str,
) -> str:
    url = " https://vk.com/" + attachment
    return await download_video_yt(url, folder)


def _randomize_time(
        orig_dt: datetime.datetime,
        delta: datetime.timedelta = datetime.timedelta(minutes=600)
) -> datetime.datetime:
    delta_seconds = int(delta.total_seconds())
    rand_seconds = random.randint(-delta_seconds, delta_seconds)
    return orig_dt + datetime.timedelta(seconds=rand_seconds)
