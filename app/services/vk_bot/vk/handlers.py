import logging
import os
import random
from pprint import pformat
from typing import Callable, Awaitable

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from vk_api.bot_longpoll import VkBotMessageEvent

from app.db import (
    triggers_answers as triggers_answers_db,
)
from app.db import (
    polls as polls_db,
    know_ids as know_ids_db,
    triggers_history as triggers_history_db,
)
from app.business_logic.vk import (
    post_in_group_wall,
    GroupPostMode,
    download_video as download_video_vk,
)
from app.models.vk_messages import (
    VkMessage as VkMessageDb,
)
from app.utils.files import TempUrlFile, DOWNLOADS_DIR
from app.utils.vk_client import VkClient
from app.schemas.images import ImageTags
from app.schemas.polls import PollCreate, PollServices
from app.schemas.triggers_answers import Answer
from app.schemas.triggers_history import TriggersHistoryNew
from app.schemas.vk import Message
from . import callbacks
from . import commands
from app.services.vk_bot.models.vk import PhotoSize, VkMessageAttachment, VkMessage
from app.services.vk_bot.service import VkBotService
from app.services.utils.client import UtilsClient

logger = logging.getLogger(__name__)

backslash_n = "\n"  # Expression fragments inside f-strings cannot include backslashes

VOTES_MAP = {
    "💀": True,
    "Нет (no)": False,
}
VOTES_THRESHOLD = 2


async def on_new_message(service: VkBotService, event: VkBotMessageEvent):
    message_model = _validate_message(event)
    if not message_model:
        return
    config = service.config

    logger.info(pformat(message_model.model_dump()))
    from_chat = message_model.from_chat
    peer_id = message_model.peer_id if event.from_chat else message_model.from_id
    from_id = message_model.from_id

    async with service.db_helper.get_session() as session:
        await _save_vk_message(session, message_model)

        if await _on_command(service, message_model):
            return

        # Find tags of images
        tags_models = await _parse_attachments_tags(
            service.utils_client, message_model.attachments
        )
        logger.info(f"{tags_models=}")
        if tags_models:
            await _send_tags(service.client_vk, tags_models, peer_id)

        # Find triggers, send answer

        find_triggers = await triggers_answers_db.get_for_like(
            session,
            f"{message_model.text}{''.join([t.tags_text + str(t.description) for t in tags_models])}",
        )
        logger.info(f"{find_triggers=}")
        answers = list(set(sum([i.answers for i in find_triggers], [])))
        know_id = await know_ids_db.get_by_vk_id(session, from_id)
        know_id_place = f"({know_id.name})" if know_id else ""
        if answers:
            answer: Answer = random.choice(answers)
            await service.client_vk.messages.send(
                peer_id=peer_id,
                message=Message(
                    text=f"{f'@id{from_id} {know_id_place}' if from_chat else ''} {answer.answer}",
                    attachment=answer.attachment,
                ),
            )
            await triggers_history_db.create(
                session,
                TriggersHistoryNew(
                    trigger_answer_id=answer.id,
                    vk_id=from_id,
                    message_data=message_model,
                ),
            )

        # answer gpt
        if (
                str(config.vk.main_group_id) in message_model.text
                or config.vk.main_group_alias in message_model.text
                or (
                message_model.reply_message
                and message_model.reply_message.from_id == -config.vk.main_group_id
        )
                or not from_chat
        ):
            try:
                payload_text = ""
                if message_model.reply_message and message_model.reply_message.text:
                    payload_text = message_model.reply_message.text + "\n"
                payload_text += message_model.text

                response_message = await service.utils_client.gpt_chat(
                    from_id,
                    payload_text,
                )
                if response_message:
                    await service.client_vk.messages.send(
                        peer_id=peer_id,
                        message=Message(
                            text=f"{f'@id{from_id} {know_id_place}' if from_chat else ''} {response_message.message}",
                        ),
                    )
            except Exception as e:
                logger.error(e)

        # Posting on group wall
        if from_chat and peer_id == 2000000001:
            for a in message_model.attachments:
                if a.type == "photo" and a.photo:
                    url = a.photo.sizes[0].url
                    async with TempUrlFile(url) as tmp:
                        if tmp:
                            await service.s3_client.upload_file("memes", "tmp/image/", tmp.filepath)
                if a.type == "video" and a.video:
                    poll_db = await polls_db.create(
                        session,
                        PollCreate(key=a.video.attachment_str, service=PollServices.VK),
                    )

                    poll = await service.client_vk.polls.create(
                        question=str(poll_db.id), add_answers=list(VOTES_MAP.keys())
                    )
                    await service.client_vk.messages.send(
                        peer_id=peer_id,
                        message=Message(text="mems?", attachment=poll.attachment_str),
                    )
                    logger.info(f"Created poll {poll_db}")



async def on_message_reply(service: VkBotService, event: VkBotMessageEvent):
    message_model = _validate_reply_message(event)
    if not message_model:
        return
    logger.info(pformat(message_model.model_dump()))
    async with service.db_helper.get_session() as session:
        await _save_vk_message(session, message_model)


async def on_callback_event(service: VkBotService, event: VkBotMessageEvent):
    callbacks_map: dict[str, Callable[[VkBotService, VkBotMessageEvent], Awaitable]] = {
        "help_callback": callbacks.help_callback
    }

    logger.info(pformat(event.object))
    callback_str = event.object["payload"]["type"]
    callback = callbacks_map.get(callback_str, None)
    if callback is not None:
        await callback(service, event)
        return
    else:
        logger.info(f"Not found callback for {callback_str}")


async def on_poll_vote(service: VkBotService, event: VkBotMessageEvent):
    try:
        poll_id, answer_id, user_id = (
            event.object["poll_id"],
            event.object["option_id"],
            event.object["user_id"],
        )
    except KeyError as e:
        logger.error(e)
        return

    poll = await service.client_vk.polls.get_by_id(poll_id)
    if not poll:
        logger.error(f"Poll not found: {poll_id}")

    try:
        poll_id_db = int(poll.question)
    except (
            TypeError,
            ValueError,
    ) as e:
        logger.error(e)
        return

    vote_result: bool | None = None
    for answer in poll.answers:
        if answer.votes >= VOTES_THRESHOLD:
            vote_result = VOTES_MAP.get(answer.text)

    if vote_result is not None:
        async with service.db_helper.get_session() as session:
            poll_db = await polls_db.disable(session, poll_id_db)
        if not poll_db:
            logger.info(f"Not found poll id {poll_id_db}")
            return

        logger.info(f"Drop Voting[{vote_result}] {poll_db}")

        if vote_result:
            download_dir = DOWNLOADS_DIR
            try:
                fp = await download_video_vk(poll_db.key, download_dir)
                logger.info(f"Downloaded {fp}")
                await service.client_vk.upload.video_wall_and_post(fp)
                os.remove(fp)
            except Exception as e:
                logger.exception(e)

        # await service.client_vk.polls.edit(poll_id, question=str(vote_result))


async def _on_command(service: VkBotService, message_model: VkMessage) -> bool:
    command_call = None
    for k, v in commands.COMMANDS_MAP.items():
        if message_model.text.strip().startswith(k):
            command_call = v
            break

    if command_call:
        await command_call(service, message_model)
        return True
    return False


def _validate_message(event: VkBotMessageEvent) -> VkMessage | None:
    try:
        return VkMessage(**dict(event.message), from_chat=event.from_chat)
    except ValidationError as e:
        logger.exception(e)
        logger.info(event.message)
        return None


def _validate_reply_message(event: VkBotMessageEvent) -> VkMessage | None:
    try:
        return VkMessage(**dict(event.object), from_chat=event.from_chat)
    except ValidationError as e:
        logger.exception(e)
        logger.info(event.message)
        return None


async def _parse_attachments_tags(
        utils_client: UtilsClient, attachments: list[VkMessageAttachment]
) -> list[ImageTags]:
    if not attachments:
        return []
    images_urls = _get_photos_urls_from_message(attachments)
    result = []
    for i in images_urls:
        tags_model = await utils_client.get_image_tags(i)
        if tags_model and (tags_model.tags or tags_model.description):
            result.append(tags_model)
    return result


def _get_photos_urls_from_message(attachments: list[VkMessageAttachment]) -> list[str]:
    result = []
    if attachments:
        for i in attachments:
            match i.type:
                case "photo":
                    max_img = _extract_max_size_img(i.photo.sizes)
                    result.append(max_img.url)
                case "video":
                    max_img = _extract_max_size_img(i.video.image)
                    result.append(max_img.url)
                case "wall":
                    result += _get_photos_urls_from_message(
                        attachments=i.wall.attachments
                    )
                case "doc":
                    if i.doc.preview and i.doc.preview.photo:
                        max_img = _extract_max_size_img(i.doc.preview.photo.sizes)
                        result.append(max_img.src)
                case _:
                    logger.info(f"Unsupported attachment media: {i}")
    return result


def _extract_max_size_img(sizes: list[PhotoSize]):
    return max(sizes, key=lambda x: x.height)


async def _send_tags(client: VkClient, tags: list[ImageTags], peer_id: int):
    await client.messages.send(
        peer_id=peer_id,
        message=Message(
            text="\n\n".join([f"{i + 1}. {m.text()}" for i, m in enumerate(tags)])
        ),
    )


async def _save_vk_message(session: AsyncSession, message_model: VkMessage) -> VkMessageDb:
    try:
        message_db = VkMessageDb(
            from_id=message_model.from_id,
            peer_id=message_model.peer_id,
            from_chat=message_model.from_chat,
            from_bot=message_model.from_id < 0,
            reply_message=message_model.reply_message.model_dump() if message_model.reply_message else None,
            attachments=message_model.model_dump().get("attachments", {}),
            date=message_model.date,
            text=message_model.text,
        )
        session.add(message_db)
        await session.commit()
        return message_db
    except Exception as e:
        logger.exception(e)
