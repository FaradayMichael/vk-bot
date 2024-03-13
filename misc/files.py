import asyncio
import logging
import os
import uuid
from typing import Any

import aiohttp
from fastapi import UploadFile
from pydantic import BaseModel

from misc.dataurl import DataURL

logger = logging.getLogger(__name__)

url_alias = str

filepath_alias = str


class TempFileModel(BaseModel):
    filepath: filepath_alias
    content_type: str | None = None


class TempFileBase:

    def __init__(
            self,
            file_obj: Any
    ):
        self.file_obj = file_obj

        self.file_model: TempFileModel | None = None

    async def __aenter__(self) -> TempFileModel:
        raise NotImplementedError()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.file_model:
            try:
                await asyncio.to_thread(
                    os.remove,
                    self.file_model.filepath
                )
            except FileNotFoundError as e:
                logger.exception(e)


class TempUploadFile(TempFileBase):

    def __init__(self, file_obj: UploadFile):
        super().__init__(file_obj)

    async def __aenter__(self) -> TempFileModel:
        self.file_obj: UploadFile
        self.file_model = TempFileModel(
            filepath=f"static/{uuid.uuid4().hex}_{self.file_obj.filename}",
            content_type=self.file_obj.content_type
        )
        with open(self.file_model.filepath, 'wb') as f:
            data = await self.file_obj.read()
            await asyncio.to_thread(
                f.write,
                data
            )
        return self.file_model


class TempUrlFile(TempFileBase):

    def __init__(self, file_obj: url_alias):
        super().__init__(file_obj)

    async def __aenter__(self) -> TempFileModel | None:
        self.file_model = await download_file(self.file_obj, folder='static', basename=uuid.uuid4().hex)
        return self.file_model


class TempBase64File(TempFileBase):

    def __init__(
            self,
            file_obj: DataURL,
    ):
        super().__init__(file_obj)

    async def __aenter__(self) -> TempFileModel:
        self.file_obj: DataURL
        self.file_model = TempFileModel(
            filepath=f"static/{uuid.uuid4().hex}.{self.file_obj.ext()}",
            content_type=self.file_obj.mimetype
        )
        with open(self.file_model.filepath, 'wb') as f:
            await asyncio.to_thread(
                f.write,
                self.file_obj.data
            )
        return self.file_model


async def download_file(
        url: str,
        folder: str = 'static',
        basename: str | None = None,  # name without ext
        max_length: int = 104857600  # 100 MB
) -> TempFileModel | None:
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

            logger.info(resp.headers)
            length = int(resp.headers.get('Content-Length', 0))
            content_type = resp.headers.get('Content-Type', None)
            if not length:
                logger.info(f"Response has no 'Content-Length'")
                return None
            if length > max_length:
                logger.info(f"File is too large: {url=} {length=}")
                return None

            with open(filepath, 'wb') as f:
                f.write(await resp.read())
    return TempFileModel(
        filepath=filepath,
        content_type=content_type
    )
