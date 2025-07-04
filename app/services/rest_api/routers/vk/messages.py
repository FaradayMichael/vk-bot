import datetime
import logging

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.business_logic import vk as vk_bl
from app.db import (
    tasks as tasks_db
)
from app.schemas.vk import (
    Message,
    SendMessage
)
from app.schemas.vk.io import (
    SendMessageInput,
    SendMessageResponse,
    MessagesHistoryResponse
)
from app.services.vk_bot.models.vk import VkMessage
from app.utils.db import (
    Session as DBSession,
)
from app.utils.fastapi.depends.db import (
    get as get_db
)
from app.utils.fastapi.depends.session import (
    get as get_session
)
from app.utils.fastapi.depends.vk_client import (
    get as get_vk_client
)
from app.utils.files import TempBase64File
from app.utils.fastapi.handlers import error_403
from app.utils.fastapi.session import Session
from app.utils.vk_client import VkClient

logger = logging.getLogger(__name__)

_prefix = '/messages'

router = APIRouter(
    prefix=_prefix,
)

admin_router = APIRouter(
    prefix=_prefix,
)


@admin_router.post('/send', response_model=SendMessageResponse)
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


@router.get('/history', response_model=MessagesHistoryResponse)
async def api_get_history(
        from_id: int | None = None,
        peer_id: int | None = None,
        from_dt: datetime.datetime = datetime.datetime.now(),
        to_dt: datetime.datetime = datetime.datetime.now(),
        conn: DBSession = Depends(get_db),
        session: Session = Depends(get_session)
) -> MessagesHistoryResponse | JSONResponse:
    """
        Limit 300 items
    """

    limit = 300
    allowed_ids = (2000000001,)
    if not session.is_admin and (not peer_id or peer_id not in allowed_ids):
        return await error_403("This peer_id is not allowed")

    tasks = await tasks_db.get_list(
        session=conn,
        from_dt=from_dt,
        to_dt=to_dt,
        funcs_in=['on_new_message']
    )

    result = []
    total = 0
    for task in tasks:
        try:
            data = task.args or task.kwargs
            vk_message = VkMessage.model_validate(_find_item(data, 'message'))
            vk_message.from_chat = vk_message.peer_id >= 200000000

            if from_id and from_id != vk_message.from_id:
                continue
            if peer_id and peer_id != vk_message.peer_id:
                continue

            result.append(vk_message)
            total += 1
            if total >= limit:
                break
        except Exception as e:
            logger.error(e)

    return MessagesHistoryResponse(
        total=len(result),
        items=result
    )


def _find_item(obj, key):
    if key in obj:
        return obj[key]
    for k, v in obj.items():
        if isinstance(v, dict):
            item = _find_item(v, key)
            if item is not None:
                return item
