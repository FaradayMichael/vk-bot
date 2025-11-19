import fastapi

from app.utils.vk_client import VkClient


async def get(request: fastapi.Request) -> VkClient:
    try:
        utils_client = request.app.state.utils_client
    except AttributeError:
        raise RuntimeError("Application state has no configs")
    else:
        return utils_client
