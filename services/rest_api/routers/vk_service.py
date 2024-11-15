import logging

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from redis.asyncio import Redis

from db import (
    send_on_schedule as send_on_schedule_db
)
from misc.consts import VK_SERVICE_REDIS_QUEUE
from misc.db import Connection
from misc.handlers import error_500
from misc.redis import publish
from misc.depends.db import (
    get as get_conn
)
from misc.depends.redis import (
    get as get_redis
)
from models.base import SuccessResponse
from models.send_on_schedule import (
    SendOnScheduleSuccessResponse,
    SendOnScheduleNew
)
from models.vk.io import WallPostInput
from models.vk.redis import (
    RedisCommands,
    RedisCommandData,
    RedisMessage
)
from services.rest_api.depends.rpc import get_vk
from services.vk_bot.client import VkBotClient

logger = logging.getLogger(__name__)

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


@admin_router.post('/send_on_schedule_tasks', response_model=SendOnScheduleSuccessResponse)
async def api_create_send_on_schedule_task(
        data: SendOnScheduleNew,
        redis: Redis = Depends(get_redis),
        conn: Connection = Depends(get_conn)
) -> SendOnScheduleSuccessResponse | JSONResponse:
    result = await send_on_schedule_db.create(
        conn,
        data
    )
    if not result:
        return await error_500("Failed to create send_on_schedule task")

    message = RedisMessage(
        command=RedisCommands.SEND_ON_SCHEDULE_RESTART,
    )
    redis_result = await publish(
        redis,
        VK_SERVICE_REDIS_QUEUE,
        message.model_dump()
    )
    if not redis_result:
        logger.error(f"Failed to send redis command: {message}")

    return SendOnScheduleSuccessResponse(data=result)


@admin_router.post('/rpc/wall_post', response_model=SuccessResponse)
async def api_rpc_wall_post(
        data: WallPostInput,
        vk_bot_client: VkBotClient = Depends(get_vk)
) -> SuccessResponse | JSONResponse:
    await vk_bot_client.vk_bot_post(
        yt_url=data.yt_url,
    )
    return SuccessResponse()
