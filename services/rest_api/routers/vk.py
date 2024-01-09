from fastapi import APIRouter, Depends

from business_logic.vk import base64_to_vk_attachment
from misc.config import Config
from misc.depends.conf import (
    get as get_conf
)
from misc.vk_client import VkClient
from models.vk import Message, SendMessageInput

router = APIRouter(
    prefix='/vk',
    tags=['vk']
)


@router.post('/send_message')
async def api_send_message_vk(
        data: SendMessageInput,
        config: Config = Depends(get_conf)
):
    client = await VkClient.create(config)

    attachments = []
    if data.message.attachments:
        attachments = await base64_to_vk_attachment(
            client,
            data.peer_id,
            data.message.attachments
        )

    await client.send_message(
        data.peer_id,
        Message(
            text=data.message.text,
            attachment=','.join(attachments) if attachments else None
        )
    )
    await client.close()



