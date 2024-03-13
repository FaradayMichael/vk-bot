from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from business_logic import (
    vk as vk_bl
)
from misc.depends.vk_client import (
    get as get_vk_client
)
from misc.files import TempBase64File
from misc.vk_client import VkClient
from models.vk import (
    Message,
    SendMessage
)
from models.vk.io import (
    SendMessageInput,
    SendMessageResponse
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
        vk_client: VkClient = Depends(get_vk_client)
) -> SendMessageResponse | JSONResponse:
    vk_attachments = []
    if data.message.attachments:
        for attachment in data.message.attachments:
            async with TempBase64File(attachment.file) as tmp:
                if a := await vk_bl.file_to_vk_attachment(vk_client, data.peer_id, tmp.filepath, attachment.type):
                    vk_attachments.append(a)

    message = Message(
        text=data.message.text,
        attachment=','.join(vk_attachments) if vk_attachments else None
    )
    await vk_client.messages.send(
        data.peer_id,
        message
    )

    return SendMessageResponse(
        data=SendMessage(
            peer_id=data.peer_id,
            message=message
        )
    )
