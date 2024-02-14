from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from business_logic.vk import base64_to_vk_attachment
from misc.config import Config
from misc.depends.conf import (
    get as get_conf
)
from misc.vk_client import VkClient
from models.vk import (
    Message,
    SendMessageInput,
    SendMessageResponse,
    SendMessage
)

router = APIRouter(
    prefix='/vk',
    tags=['vk']
)


@router.post('/send_message', response_model=SendMessageResponse)
async def api_send_message_vk(
        data: SendMessageInput,
        config: Config = Depends(get_conf)
) -> SendMessageResponse | JSONResponse:
    client = VkClient(config)

    attachments = []
    if data.message.attachments:
        attachments = await base64_to_vk_attachment(
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
