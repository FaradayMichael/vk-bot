import fastapi

from app.utils.vk_client import VkClient


async def get(request: fastapi.Request) -> VkClient:
    try:
        config = request.app.state.config
    except AttributeError:
        raise RuntimeError('Application state has no configs')
    else:
        client = VkClient(config.vk)
        yield client
        await client.close()
