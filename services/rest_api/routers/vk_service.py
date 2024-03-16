from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from redis.asyncio import Redis

from misc.consts import VK_SERVICE_REDIS_QUEUE
from misc.redis import publish
from misc.depends.redis import (
    get as get_redis
)
from models.base import SuccessResponse
from models.vk.redis import (
    RedisCommands,
    RedisCommandData,
    RedisMessage
)

_prefix = '/vk_service'
_tags = ['vk_service']

router = APIRouter(
    prefix=_prefix,
    tags=_tags
)

admin_router = APIRouter(
    prefix=_prefix,
    tags=_tags
)


@admin_router.post('/send_command', response_model=SuccessResponse)
async def api_send_command(
        command: RedisCommands,
        data: RedisCommandData,
        redis: Redis = Depends(get_redis)
) -> SuccessResponse | JSONResponse:
    message = RedisMessage(
        command=command,
        **data.model_dump()
    )
    result = await publish(
        redis,
        VK_SERVICE_REDIS_QUEUE,
        message.model_dump()
    )
    return SuccessResponse(data=result)
