import logging
import random
from pprint import pformat
from typing import Callable, Awaitable

from pydantic import ValidationError
from vk_api.bot_longpoll import VkBotMessageEvent

from db import (
    triggers_answers as triggers_answers_db,
    know_ids as know_ids_db,
    triggers_history as triggers_history_db
)
from business_logic.vk import (
    parse_image_tags,
    post_in_group_wall,
    GroupPostMode
)
from misc.files import TempUrlFile
from misc.vk_client import VkClient
from models.images import (
    ImageTags
)
from models.triggers_answers import Answer
from models.triggers_history import TriggersHistoryNew
from models.vk import (
    Message
)
from . import callbacks
from . import commands
from services.vk_bot.models.vk import (
    PhotoSize,
    VkMessageAttachment,
    VkMessage
)
from services.vk_bot.service import VkBotService

logger = logging.getLogger(__name__)

backslash_n = '\n'  # Expression fragments inside f-strings cannot include backslashes


async def on_new_message(service: VkBotService, event: VkBotMessageEvent):
    message_model = _validate_message(event)
    if not message_model:
        return

    logger.info(pformat(message_model.model_dump()))
    from_chat = message_model.from_chat
    peer_id = message_model.peer_id if event.from_chat else message_model.from_id
    from_id = message_model.from_id

    if await _on_command(service, message_model):
        return

    # Find tags of images
    tags_models = await _parse_attachments_tags(message_model.attachments)
    logger.info(f"{tags_models=}")
    if tags_models:
        await _send_tags(service.client_vk, tags_models, peer_id)

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
            answer: Answer = random.choice(answers)
            know_id = await know_ids_db.get(conn, from_id)
            know_id_place = f"({know_id.name})" if know_id else ''
            await service.client_vk.messages.send(
                peer_id=peer_id,
                message=Message(
                    text=f"{f'@id{from_id} {know_id_place}' if from_chat else ''} {answer.answer}",
                    attachment=answer.attachment
                )
            )
            try:
                await triggers_history_db.create(
                    conn,
                    TriggersHistoryNew(
                        trigger_answer_id=answer.id,
                        vk_id=from_id,
                        message_data=message_model
                    )
                )
            except Exception as e:
                logger.error(e)

    # Posting on group wall
    if from_chat and peer_id == 2000000001:
        photo_attachments_from_msg = []
        for a in message_model.attachments:
            if a.type == 'photo' and a.photo:
                url = a.photo.sizes[0].url
                async with TempUrlFile(url) as tmp:
                    if tmp:
                        photo_attachments_from_msg += await service.client_vk.upload.photo_wall(
                            [tmp.filepath]
                        )
        if photo_attachments_from_msg:
            await post_in_group_wall(
                service.client_vk,
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


async def _on_command(
        service: VkBotService,
        message_model: VkMessage
) -> bool:
    command_call = None
    for k, v in commands.COMMANDS_MAP.items():
        if message_model.text.strip().startswith(k):
            command_call = v
            break

    if command_call:
        await command_call(service, message_model)
        return True
    return False


def _validate_message(
        event: VkBotMessageEvent
) -> VkMessage | None:
    try:
        return VkMessage(
            **dict(event.message),
            from_chat=event.from_chat
        )
    except ValidationError as e:
        logger.exception(e)
        logger.info(event.message)
        return None


async def _parse_attachments_tags(
        attachments: list[VkMessageAttachment]
) -> list[ImageTags]:
    if not attachments:
        return []
    images_urls = _get_photos_urls_from_message(attachments)
    result = []
    for i in images_urls:
        tags_model = await parse_image_tags(i)
        if tags_model and (tags_model.tags or tags_model.description):
            result.append(tags_model)
    return result


def _get_photos_urls_from_message(
        attachments: list[VkMessageAttachment]
) -> list[str]:
    result = []
    if attachments:
        for i in attachments:
            match i.type:
                case 'photo':
                    max_img = _extract_max_size_img(i.photo.sizes)
                    result.append(max_img.url)
                case 'video':
                    max_img = _extract_max_size_img(i.video.image)
                    result.append(max_img.url)
                case 'wall':
                    result += _get_photos_urls_from_message(
                        attachments=i.wall.attachments
                    )
                case 'doc':
                    if i.doc.preview and i.doc.preview.photo:
                        max_img = _extract_max_size_img(i.doc.preview.photo.sizes)
                        result.append(max_img.src)
                case _:
                    logger.info(f"Unsupported attachment media: {i}")
    return result


def _extract_max_size_img(sizes: list[PhotoSize]):
    return max(sizes, key=lambda x: x.height)


async def _send_tags(
        client: VkClient,
        tags: list[ImageTags],
        peer_id: int
):
    await client.messages.send(
        peer_id=peer_id,
        message=Message(
            text='\n\n'.join(
                [
                    f"{i + 1}. {m.text()}"
                    for i, m in enumerate(tags)
                ]
            )
        )
    )
