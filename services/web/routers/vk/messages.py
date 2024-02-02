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

from misc.config import Config
from misc.db import Connection
from misc.depends.db import (
    get as get_conn
)
from misc.depends.conf import (
    get as get_conf
)
from misc.depends.session import (
    get as ges_session
)
from misc.depends.jinja import (
    get as get_jinja
)
from misc.files import TempFile
from misc.session import Session
from misc.vk_client import VkClient

from models.vk import AttachmentType, Message

router = APIRouter(prefix='/messages')


@router.get('/', response_class=HTMLResponse)
async def vk_messages_view(
        request: Request,
        jinja: Environment = Depends(get_jinja),
        session: Session = Depends(ges_session),
        # conn: Connection = Depends(get_conn)
):
    return jinja.get_template('vk/messages.html').render(
        user=session.user,
        request=request
    )


@router.post('/', response_class=RedirectResponse)
async def send_vk_message(
        peer_id: int = Form(),
        message_text: str = Form(default=''),
        files: list[UploadFile] = File(...),
        config: Config = Depends(get_conf)
):
    client = await VkClient.create(config)

    attachments = []
    if files:
        for f in files:
            if f.size == 0:
                continue

            async with TempFile(f) as file_path:
                attachments.append(
                    await file_to_vk_attachment(
                        client,
                        peer_id,
                        file_path,
                        AttachmentType.by_content_type(f.content_type)
                    )
                )

    await client.send_message(
        peer_id,
        Message(
            text=message_text,
            attachment=','.join(attachments) if attachments else None
        )
    )

    await client.close()
    return RedirectResponse('/vk/messages', status_code=302)
