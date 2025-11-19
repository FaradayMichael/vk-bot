import asyncio
import logging

from steam_web_api import Steam
from urllib3.exceptions import NameResolutionError

logger = logging.getLogger(__name__)


class SteamClient:

    def __init__(self, loop: asyncio.AbstractEventLoop, key: str):
        self._loop = loop
        self._client = Steam(key)

    async def get_user_details(self, steamid: str) -> dict:
        result = await self._run_async(self._client.users.get_user_details, steamid)
        return result.get("player") if result else {}

    async def _run_async(self, func, *args):
        try:
            return await self._loop.run_in_executor(None, func, *args)
        except NameResolutionError:
            raise
        except Exception as e:
            logger.error(e)
            return {}
