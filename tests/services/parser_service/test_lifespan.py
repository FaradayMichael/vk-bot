import asyncio

import pytest

from misc.config import Config
from services.parser_service.service import ParserService


@pytest.mark.asyncio
async def test_parser_service(
        conf: Config,
        #event_loop
):
    loop = asyncio.get_event_loop()
    service = await ParserService.create(conf, loop)
    await asyncio.sleep(5)
    service.stop()
