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
    parse_image_tags,
    post_in_group_wall, GroupPostMode
)
from misc.files import TempUrlFile
from models.images import (
    ImageTags
)
from models.triggers_answers import AnswerBase
from models.vk import (
    Message
)
from . import callbacks
from .models import (
    VkMessage,
    VkMessageAttachment,
    PhotoSize
)
from .service import VkBotService

logger = logging.getLogger(__name__)

backslash_n = '\n'  # Expression fragments inside f-strings cannot include backslashes


async def on_new_message(service: VkBotService, event: VkBotMessageEvent):
    async def on_command(command: str) -> bool:

        async def on_help():
            await service.client.messages.send(
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
        await service.client.messages.send(
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
            await service.client.messages.send(
                peer_id=peer_id,
                message=Message(
                    text=f"{f'@id{from_id} ' if from_chat else ''} {answer.answer}",
                    attachment=answer.attachment
                )
            )

    # Posting on group wall
    photo_attachments_from_msg = []
    for a in message_model.attachments:
        if a.type == 'photo' and a.photo:
            url = a.photo.sizes[0].url
            async with TempUrlFile(url) as tmp:
                photo_attachments_from_msg += await service.client.upload.photo_wall(
                    [tmp]
                )
    if photo_attachments_from_msg:
        await post_in_group_wall(
            service.client,
            message_text='',
            attachments=photo_attachments_from_msg,
            mode=GroupPostMode.COMPILE_9,
            notify=True
        )


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
                case 'doc':
                    if i.doc.preview and i.doc.preview.photo:
                        max_img = extract_max_size_img(i.doc.preview.photo.sizes)
                        result.append(max_img.src)
                case _:
                    logger.info(f"Unsupported attachment media: {i}")
    return result


def extract_max_size_img(sizes: list[PhotoSize]):
    return max(sizes, key=lambda x: x.height)
