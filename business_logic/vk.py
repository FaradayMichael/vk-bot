import asyncio
import logging
import uuid
from typing import assert_never

from misc.vk_client import VkClient
from models.vk import AttachmentInput, AttachmentType

logger = logging.getLogger(__name__)


async def parse_attachments(
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
