import logging

import fastapi

from misc import db

logger = logging.getLogger(__name__)


async def get(request: fastapi.Request) -> db.Connection:
    try:
        pool = request.app.state.db_pool
    except AttributeError:
        raise RuntimeError('Application state has no db pool')
    else:
        async with pool.acquire() as conn:
            yield conn

async def get_pool(request: fastapi.Request) -> db.Pool:
    try:
        pool = request.app.state.db_pool
    except AttributeError:
        raise RuntimeError('Application state has no db pool')
    else:
        yield pool