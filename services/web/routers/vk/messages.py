from fastapi import (
    APIRouter,
    Depends,
    Request,
    Form,
    File,
    UploadFile
)
from fastapi.responses import (
    HTMLResponse,
    RedirectResponse
)
from jinja2 import Environment

from business_logic.vk import file_to_vk_attachment
from db import (
    know_ids as know_ids_db
)
from misc.db import Connection
from misc.depends.db import (
    get as get_conn
)
from misc.depends.vk_client import (
    get as get_vk_client
)
from misc.depends.session import (
    get as ges_session
)
from misc.depends.jinja import (
    get as get_jinja
)
from misc.files import TempUploadFile
from misc.session import Session
from misc.vk_client import VkClient

from models.vk import Message
from models.base import AttachmentType

router = APIRouter(prefix='/messages')


@router.get('/', response_class=HTMLResponse)
async def vk_messages_view(
        request: Request,
        jinja: Environment = Depends(get_jinja),
        session: Session = Depends(ges_session),
        conn: Connection = Depends(get_conn)
):
    know_ids = await know_ids_db.get_all(conn)
    return jinja.get_template('vk/messages.html').render(
        user=session.user,
        request=request,
        know_ids=know_ids
    )


@router.post('/', response_class=RedirectResponse)
async def send_vk_message(
        peer_id: int = Form(),
        message_text: str = Form(default=''),
        files: list[UploadFile] = File(...),
        vk_client: VkClient = Depends(get_vk_client)
):
    attachments = []
    if files:
        for f in files:
            if f.size == 0:
                continue

            async with TempUploadFile(f) as tmp:
                attachments.append(
                    await file_to_vk_attachment(
                        vk_client,
                        peer_id,
                        tmp.filepath,
                        AttachmentType.by_content_type(f.content_type)
                    )
                )

    await vk_client.messages.send(
        peer_id,
        Message(
            text=message_text,
            attachment=','.join(attachments) if attachments else None
        )
    )

    return RedirectResponse('/vk/messages', status_code=302)
