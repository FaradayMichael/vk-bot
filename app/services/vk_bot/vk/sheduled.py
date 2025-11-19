import asyncio
import datetime
import logging
from typing import Callable, Any, Awaitable

import croniter

from app.schemas.vk import Message
from app.services.vk_bot.service import VkBotService

logger = logging.getLogger(__name__)


async def send_on_schedule(
    service: VkBotService,
    cron: str,
    peer_id: int | None = None,
    message: Message | None = None,
    fetch_message_data_func: (
        Callable[[Any | None], Awaitable[tuple[int, Message]]] | None
    ) = None,
    args: tuple = (),
    kwargs: dict | None = None,
):
    if kwargs is None:
        kwargs = {}

    while not service.stopping:
        try:
            if (peer_id is None or message is None) and fetch_message_data_func is None:
                raise ValueError(
                    "One of (peer_id, message) or fetch_message_data_func is required"
                )

            now = datetime.datetime.now()
            nxt: datetime.datetime = croniter.croniter(cron, now).get_next(
                datetime.datetime
            )
            sleep = (nxt - now).total_seconds()
            logger.info(
                f"Schedule {sleep=} {peer_id=} {message=} {fetch_message_data_func=}"
            )
            await asyncio.sleep(sleep)

            peer_id, message = (
                await fetch_message_data_func(*args, **kwargs)
                if fetch_message_data_func
                else (peer_id, message)
            )

            await service.execute_in_worker(
                service.client_vk.messages.send, peer_id, message
            )
        except (GeneratorExit, asyncio.CancelledError, KeyboardInterrupt):
            break
        except Exception as e:
            logger.exception(e)
            service.ex.append(e)
            await asyncio.sleep(300)
