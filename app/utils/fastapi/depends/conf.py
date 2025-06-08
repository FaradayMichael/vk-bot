import logging

import fastapi

from app.utils.config import Config

logger = logging.getLogger(__name__)


async def get(request: fastapi.Request) -> Config:
    try:
        return request.app.state.config
    except AttributeError:
        raise RuntimeError('Application state has no configs')
