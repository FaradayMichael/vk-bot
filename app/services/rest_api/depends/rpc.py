import logging

import fastapi

from app.services.vk_bot.client import VkBotClient
from app.utils.fastapi.state import State

logger = logging.getLogger()

def get_vk(request: fastapi.Request) -> VkBotClient:
    try:
        state: State = request.app.state
        return state.vk_bot_client
    except AttributeError as e:
        logger.exception(e)

