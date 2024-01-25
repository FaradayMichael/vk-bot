import logging
import random
from pprint import pformat

from pydantic import ValidationError
from vk_api.bot_longpoll import VkBotMessageEvent

from db import (
    triggers_answers as triggers_answers_db
)
from business_logic.vk import (
    parse_image_tags
)
from models.images import (
    ImageTags
)
from models.triggers_answers import AnswerBase
from models.vk import (
    Message
)
from .models import (
    VkMessage,
    VkMessageAttachment,
    PhotoSize
)
from .service import VkBotService

logger = logging.getLogger(__name__)

backslash_n = '\n'  # Expression fragments inside f-strings cannot include backslashes


async def on_new_message(service: VkBotService, event: VkBotMessageEvent):
    message_model = validate_message(event)
    if not message_model:
        return

    logger.info(pformat(message_model.model_dump()))
    from_chat = event.from_chat
    peer_id = message_model.peer_id if event.from_chat else message_model.from_id
    from_id = message_model.from_id

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

    async with service.db_pool.acquire() as conn:
        find_triggers = await triggers_answers_db.get_for_like(
            conn,
            f"{message_model.text}{''.join([t.tags_text + str(t.description) for t in tags_models])}"
        )
        logger.info(find_triggers)
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
