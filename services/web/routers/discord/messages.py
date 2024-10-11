import asyncio
import logging

from discord import (
    Client,
    Intents
)
from fastapi import (
    APIRouter,
    Depends,
    Request,
    Form,
)
from fastapi.responses import (
    HTMLResponse,
    RedirectResponse
)
from jinja2 import Environment

from misc.config import Config
from misc.depends.conf import (
    get as get_config
)
from misc.depends.session import (
    get as ges_session
)
from misc.depends.jinja import (
    get as get_jinja
)
from misc.session import Session

logger = logging.getLogger(__name__)

router = APIRouter(prefix='/messages')


@router.get('/', response_class=HTMLResponse)
async def discord_messages_view(
        request: Request,
        jinja: Environment = Depends(get_jinja),
        session: Session = Depends(ges_session),
):
    return jinja.get_template('/discord/messages.html').render(
        user=session.user,
        request=request,
    )


@router.post('/', response_class=RedirectResponse)
async def send_discord_message(
        peer_id: int = Form(),
        message_text: str = Form(default=''),
        # files: list[UploadFile] = File(...),
        config: Config = Depends(get_config)
):
    intents = Intents.all()
    intents.messages = True
    client = Client(intents=intents)
    task = asyncio.create_task(client.start(config.discord.token))
    for i in range(10):
        if client.is_ready():
            break
        logger.info(f'Waiting for client ready {i + 1}...')
        await asyncio.sleep(3)
    channel = client.get_channel(peer_id)
    if not channel:
        return HTMLResponse(status_code=404, content="Channel not found")
    await channel.send(message_text)
    await client.close()
    try:
        task.cancel()
    except Exception as e:
        logger.error(e)

    return RedirectResponse('/discord/messages', status_code=302)
