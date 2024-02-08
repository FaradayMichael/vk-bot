import asyncio
import logging
import os
import uuid

import aiohttp
from fastapi import UploadFile

logger = logging.getLogger(__name__)


class TempFileBase:

    def __init__(
            self
    ):
        self.filepath = None

    async def __aenter__(self) -> str:
        raise NotImplementedError()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.filepath:
            try:
                await asyncio.to_thread(
                    os.remove,
                    self.filepath
                )
            except FileNotFoundError as e:
                logger.exception(e)


class TempUploadFile(TempFileBase):

    def __init__(self, file: UploadFile):
        super().__init__()
        self.file = file
        self.filepath = None

    async def __aenter__(self) -> str:
        self.filepath = f"static/{uuid.uuid4().hex}_{self.file.filename}"
        with open(self.filepath, 'wb') as f:
            data = await self.file.read()
            await asyncio.to_thread(
                f.write,
                data
            )
        return self.filepath


class TempUrlFile(TempFileBase):

    def __init__(self, url: str):
        super().__init__()
        self.url = url
        self.filepath = None

    async def __aenter__(self) -> str:
        self.filepath = await download_file(self.url, folder='static', basename=uuid.uuid4().hex)
        return self.filepath


async def download_file(
        url: str,
        folder: str = 'static',
        basename: str | None = None  # name without ext
) -> str | None:
    filename = os.path.basename(url)
    if '?' in filename:
        filename = filename.split('?')[0]
    if basename:
        filename = f"{basename}{os.path.splitext(filename)[-1]}"
    filepath = os.path.join(folder, filename)
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status >= 400:
                return None
            with open(filepath, 'wb') as f:
                f.write(await resp.read())
    return filepath
