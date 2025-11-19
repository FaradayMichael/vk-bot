import logging

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from redis.asyncio import Redis

from app.db import send_on_schedule as send_on_schedule_db
from app.schemas.base import SuccessResponse
from app.schemas.send_on_schedule import SendOnSchedule, SendOnScheduleNew
from app.schemas.vk.io import WallPostInput
from app.schemas.vk.redis import RedisCommands, RedisCommandData, RedisMessage
from app.services.rest_api.depends.rpc import get_vk
from app.services.vk_bot.client import VkBotClient
from app.utils.consts import VK_SERVICE_REDIS_QUEUE
from app.utils.db import (
    Session as DBSession,
)
from app.utils.fastapi.handlers import error_500
from app.utils.redis import publish
from app.utils.fastapi.depends.db import get as get_db
from app.utils.fastapi.depends.redis import get as get_redis

logger = logging.getLogger(__name__)

_prefix = "/vk_service"
_tags = ["vk_service"]

router = APIRouter(prefix=_prefix, tags=_tags)

admin_router = APIRouter(prefix=_prefix, tags=_tags)


@admin_router.post("/send_command", response_model=SuccessResponse)
async def api_send_command(
    command: RedisCommands, data: RedisCommandData, redis: Redis = Depends(get_redis)
) -> SuccessResponse | JSONResponse:
    message = RedisMessage(command=command, **data.model_dump())
    result = await publish(redis, VK_SERVICE_REDIS_QUEUE, message.model_dump())
    return SuccessResponse(data=result)


@admin_router.post("/send_on_schedule_tasks", response_model=SendOnSchedule)
async def api_create_send_on_schedule_task(
    data: SendOnScheduleNew,
    redis: Redis = Depends(get_redis),
    conn: DBSession = Depends(get_db),
) -> SendOnSchedule | JSONResponse:
    result = await send_on_schedule_db.create(conn, data)
    if not result:
        return await error_500("Failed to create send_on_schedule task")

    message = RedisMessage(
        command=RedisCommands.SEND_ON_SCHEDULE_RESTART,
    )
    redis_result = await publish(redis, VK_SERVICE_REDIS_QUEUE, message.model_dump())
    if not redis_result:
        logger.error(f"Failed to send redis command: {message}")

    return result


@admin_router.post("/rpc/wall_post", response_model=SuccessResponse)
async def api_rpc_wall_post(
    data: WallPostInput, vk_bot_client: VkBotClient = Depends(get_vk)
) -> SuccessResponse | JSONResponse:
    await vk_bot_client.vk_bot_post(
        yt_url=data.yt_url,
    )
    return SuccessResponse()
