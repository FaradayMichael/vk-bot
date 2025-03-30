import logging

import fastapi
from jinja2 import Environment

logger = logging.getLogger(__name__)


async def get(request: fastapi.Request) -> Environment:
    try:
        return request.app.state.jinja
    except AttributeError:
        raise RuntimeError('Application state has no jinja environment')
