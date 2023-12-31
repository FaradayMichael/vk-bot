import logging

import fastapi
from misc.smtp import SMTP

logger = logging.getLogger(__name__)


async def get(request: fastapi.Request) -> SMTP:
    try:
        return request.app.state.smtp
    except AttributeError:
        raise RuntimeError('Application state has no smtp connection')
