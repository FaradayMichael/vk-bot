import datetime
import logging
import random
from pprint import pformat
from typing import Callable, Awaitable

from pydantic import ValidationError
from vk_api.bot_longpoll import VkBotMessageEvent

from db import (
    triggers_answers as triggers_answers_db
)
from business_logic.vk import (
    parse_image_tags
)
from misc.files import TempUrlFile
from models.images import (
    ImageTags
)
from models.triggers_answers import AnswerBase
from models.vk import (
    Message,
    WallPost
)
from . import callbacks
from .models import (
    VkMessage,
    VkMessageAttachment,
    PhotoSize,
    WallItemFilter
)
from .service import VkBotService

logger = logging.getLogger(__name__)

backslash_n = '\n'  # Expression fragments inside f-strings cannot include backslashes


async def on_new_message(service: VkBotService, event: VkBotMessageEvent):
    async def on_command(command: str) -> bool:

        async def on_help():
            await service.client.send_message(
                peer_id=peer_id,
                message=Message(
                    text=f"{f'@id{from_id} ' if from_chat else ''} help"
                ),
                keyboard=callbacks.help_kb
            )

        commands_map = {
            '/help': on_help
        }
        command_call = commands_map.get(command, None)
        if command_call:
            await command_call()
            return True
        return False

    message_model = validate_message(event)
    if not message_model:
        return

    logger.info(pformat(message_model.model_dump()))
    from_chat = event.from_chat
    peer_id = message_model.peer_id if event.from_chat else message_model.from_id
    from_id = message_model.from_id

    if message_model.text.strip().startswith('/'):
        success = await on_command(message_model.text.strip().lower())
        if success:
            return

    # Find tags of images
    tags_models = await parse_attachments_tags(message_model.attachments)
    logger.info(f"{tags_models=}")
    if tags_models:
        await service.client.send_message(
            peer_id=peer_id,
            message=Message(
                text='\n\n'.join(
                    [
                        f'tags: {i.tags_text}{backslash_n + i.description if i.description else ""}'
                        for i in tags_models
                    ]
                )
            )
        )

    # Find triggers, send answer
    async with service.db_pool.acquire() as conn:
        find_triggers = await triggers_answers_db.get_for_like(
            conn,
            f"{message_model.text}{''.join([t.tags_text + str(t.description) for t in tags_models])}"
        )
        logger.info(f"{find_triggers=}")
        answers = list(set(
            sum([i.answers for i in find_triggers], [])
        ))
        if answers:
            answer: AnswerBase = random.choice(answers)
            await service.client.send_message(
                peer_id=peer_id,
                message=Message(
                    text=f"{f'@id{from_id} ' if from_chat else ''} {answer.answer}",
                    attachment=answer.attachment
                )
            )

    try:
        # Posting on group wall
        photo_attachments_from_msg = []
        for a in message_model.attachments:
            if a.type == 'photo' and a.photo:
                url = a.photo.sizes[0].url
                async with TempUrlFile(url) as tmp:
                    photo_attachments_from_msg += await service.client.upload_photo_wall(
                        [tmp]
                    )
        if photo_attachments_from_msg:
            posts = await service.client.get_posts(WallItemFilter.POSTPONED)
            available_posts = [
                p
                for p in posts
                if len(p.attachments) + len(photo_attachments_from_msg) <= 9 and p.post_source['type'] == 'api'
            ]
            if not available_posts:
                logger.info(f'Create new post for {len(photo_attachments_from_msg)} attachments')
                await service.client.wall_post(
                    post=WallPost(
                        attachments=','.join(photo_attachments_from_msg)
                    ),
                    delay=datetime.timedelta(days=2)
                )
            else:
                available_posts.sort(key=lambda x: len(x.attachments), reverse=True)
                post = available_posts[0]

                logger.info(f"Edit {post.id=} for {len(photo_attachments_from_msg)} new attachments")

                post_attachments = [
                                       a.photo.attachment_str
                                       for a in post.attachments if a.photo
                                   ] + photo_attachments_from_msg
                await service.client.edit_post(
                    post_id=post.id,
                    attachments=','.join(post_attachments),
                    delay=datetime.timedelta(days=2 if len(post_attachments) >= 9 else 14)
                )
                if len(post_attachments) >= 9:
                    logger.info(f"{post.id=} ready to publish")
                    await service.client.send_message(
                        peer_id=service.config.vk.main_user_id,
                        message=Message(
                            text=f"{post.id=} ready to publish"
                        )
                    )

    except Exception as e:
        logger.exception(e)
        service.ex.append(e)


async def on_callback_event(service: VkBotService, event: VkBotMessageEvent):
    callbacks_map: dict[str, Callable[[VkBotService, VkBotMessageEvent], Awaitable]] = {
        'help_callback': callbacks.help_callback
    }

    logger.info(pformat(event.object))
    callback_str = event.object['payload']['type']
    callback = callbacks_map.get(callback_str, None)
    if callback is not None:
        await callback(service, event)
        return
    else:
        logger.info(f"Not found callback for {callback_str}")


def validate_message(
        event: VkBotMessageEvent
) -> VkMessage | None:
    try:
        return VkMessage.model_validate(dict(event.message))
    except ValidationError as e:
        logger.exception(e)
        logger.info(event.message)
        return None


async def parse_attachments_tags(
        attachments: list[VkMessageAttachment]
) -> list[ImageTags]:
    if not attachments:
        return []
    images_urls = get_photos_urls_from_message(attachments)
    result = []
    for i in images_urls:
        tags_model = await parse_image_tags(i)
        if tags_model and (tags_model.tags or tags_model.description):
            result.append(tags_model)
    return result


def get_photos_urls_from_message(
        attachments: list[VkMessageAttachment]
) -> list[str]:
    result = []
    if attachments:
        for i in attachments:
            match i.type:
                case 'photo':
                    max_img = extract_max_size_img(i.photo.sizes)
                    result.append(max_img.url)

                case 'video':
                    max_img = extract_max_size_img(i.video.image)
                    result.append(max_img.url)

                case 'wall':
                    result += get_photos_urls_from_message(
                        attachments=i.wall.attachments
                    )
                case _:
                    logger.info(f"Unsupported attachment media: {i}")
    return result


def extract_max_size_img(sizes: list[PhotoSize]):
    return max(sizes, key=lambda x: x.height)
