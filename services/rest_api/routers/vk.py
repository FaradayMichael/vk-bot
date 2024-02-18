from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from business_logic import (
    vk as vk_bl
)
from misc.config import Config
from misc.depends.conf import (
    get as get_conf
)
from misc.files import TempBase64File
from misc.handlers import error_400
from misc.vk_client import VkClient
from models.base import SuccessResponse
from models.vk import (
    Message,
    SendMessage,
    AttachmentType
)
from models.vk.io import (
    SendMessageInput,
    SendMessageResponse,
    WallPostInput
)

_prefix = '/vk'
_tags = ['vk']

router = APIRouter(
    prefix=_prefix,
    tags=_tags
)

admin_router = APIRouter(
    prefix=_prefix,
    tags=_tags
)


@admin_router.post('/send_message', response_model=SendMessageResponse)
async def api_send_message_vk(
        data: SendMessageInput,
        config: Config = Depends(get_conf)
) -> SendMessageResponse | JSONResponse:
    client = VkClient(config)

    attachments = []
    if data.message.attachments:
        attachments = await vk_bl.base64_to_vk_attachment(
            client,
            data.peer_id,
            data.message.attachments
        )

    message = Message(
        text=data.message.text,
        attachment=','.join(attachments) if attachments else None
    )
    await client.messages.send(
        data.peer_id,
        message
    )
    await client.close()

    return SendMessageResponse(
        data=SendMessage(
            peer_id=data.peer_id,
            message=message
        )
    )


@router.post('/wall_post', response_model=SuccessResponse)
async def api_wall_post_vk(
        data: WallPostInput,
        config: Config = Depends(get_conf)
) -> SuccessResponse | JSONResponse:
    for f in data.files:
        if AttachmentType.by_content_type(f.mimetype) is not AttachmentType.PHOTO:
            return await error_400(f"Unsupported media type: {f.mimetype}")

    client = VkClient(config)

    attachments = []
    for f in data.files:
        async with TempBase64File(f) as filepath:
            attachments += await client.upload.photo_wall([filepath])
    await vk_bl.post_in_group_wall(
        client=client,
        message_text='',
        attachments=attachments
    )

    await client.close()

    return SuccessResponse()
