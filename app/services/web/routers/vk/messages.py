from fastapi import APIRouter, Depends, Request, Form, File, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from jinja2 import Environment

from app.business_logic.vk import file_to_vk_attachment
from app.db import know_ids as know_ids_db
from app.schemas.vk import Message
from app.schemas.base import AttachmentType
from app.utils.db import (
    Session as DBSession,
)
from app.utils.fastapi.depends.db import get as get_db
from app.utils.fastapi.depends.vk_client import get as get_vk_client
from app.utils.fastapi.depends.session import get as ges_session
from app.utils.fastapi.depends.jinja import get as get_jinja
from app.utils.files import TempUploadFile
from app.utils.fastapi.session import Session
from app.utils.vk_client import VkClient


router = APIRouter(prefix="/messages")


@router.get("/", response_class=HTMLResponse)
async def vk_messages_view(
    request: Request,
    jinja: Environment = Depends(get_jinja),
    session: Session = Depends(ges_session),
    conn: DBSession = Depends(get_db),
):
    know_ids = await know_ids_db.get_list(conn)
    return jinja.get_template("vk/messages.html").render(
        user=session.user, request=request, know_ids=know_ids
    )


@router.post("/", response_class=RedirectResponse)
async def send_vk_message(
    peer_id: int = Form(),
    message_text: str = Form(default=""),
    files: list[UploadFile] = File(...),
    vk_client: VkClient = Depends(get_vk_client),
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
                        AttachmentType.by_content_type(f.content_type),
                    )
                )

    await vk_client.messages.send(
        peer_id,
        Message(
            text=message_text, attachment=",".join(attachments) if attachments else None
        ),
    )

    return RedirectResponse("/vk/messages", status_code=302)
