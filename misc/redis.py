import json
import logging
from typing import Any, Optional

from redis.asyncio import from_url, Redis

from misc.config import RedisConfig
from misc.env import get as get_from_env

logger = logging.getLogger(__name__)

Connection = Redis


async def init(config: RedisConfig) -> Connection:
    dsn = config.dsn
    if not dsn:
        raise RuntimeError('Redis connection parameters not defined')

    return await from_url(
        dsn,
        password=get_from_env('REDIS_PASS', strict=True),
        max_connections=config.maxsize
    )


async def close(pool: Connection):
    await pool.aclose()


async def get(conn: Connection, key: str) -> Optional[dict]:
    data = await conn.get(key)
    if data is not None:
        try:
            return json.loads(data)
        except:
            logger.exception(f'Wrong session data {data}')
    return None


async def set(conn: Connection, key: str, value: Any):
    await conn.set(key, json.dumps(value))


async def del_(conn: Connection, key: str):
    await conn.delete(key)


async def setex(conn: Connection, key: str, ttl: int, value: Any):
    await conn.setex(key, ttl, json.dumps(value))


async def publish(
        conn: Connection,
        queue_name: str,
        data: Any
):
    await conn.publish(queue_name, json.dumps(data))
