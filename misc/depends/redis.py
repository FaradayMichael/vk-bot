import logging

import fastapi

from misc import redis

logger = logging.getLogger(__name__)


async def get(request: fastapi.Request) -> redis.Connection:
    try:
        pool = request.app.state.redis_pool
    except AttributeError:
        raise RuntimeError('Application state has no redis pool')
    else:
        async with await pool as conn:
            yield conn
