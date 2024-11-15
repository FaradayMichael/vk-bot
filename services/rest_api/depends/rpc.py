import logging

import fastapi

from services.rest_api.state import State
from services.vk_bot.client import VkBotClient

logger = logging.getLogger()

def get_vk(request: fastapi.Request) -> VkBotClient:
    try:
        state: State = request.app.state
        return state.vk_bot_client
    except AttributeError as e:
        logger.exception(e)

