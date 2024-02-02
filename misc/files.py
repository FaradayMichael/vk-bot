import asyncio
import logging
import os
import uuid

from fastapi import UploadFile

logger = logging.getLogger(__name__)


class TempFile:

    def __init__(
            self,
            file: UploadFile
    ):
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

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.filepath:
            try:
                await asyncio.to_thread(
                    os.remove,
                    self.filepath
                )
            except FileNotFoundError as e:
                logger.exception(e)
