import logging
import os
import uuid
from contextlib import asynccontextmanager

import aiofiles
from aiobotocore.session import (
    get_session,
    AioSession,
    AioBaseClient,
)
from aiohttp import ClientError

logger = logging.getLogger(__name__)


class S3Client:

    def __init__(
            self,
            access_key: str,
            secret_key: str,
            endpoint_url: str,
    ):
        self._access_key = access_key
        self._secret_key = secret_key
        self._endpoint_url = endpoint_url
        self._config = {
            "aws_access_key_id": access_key,
            "aws_secret_access_key": secret_key,
            "endpoint_url": endpoint_url,
        }
        self._session: AioSession | None = None

    async def init(self):
        self._session = get_session()

    async def close(self):
        self._session = None

    @asynccontextmanager
    async def get_client(self) -> AioBaseClient:
        async with self._session.create_client("s3", **self._config) as client:
            yield client

    async def download(
            self,
            bucket: str,
            path: str,
            folder: str = 'static',
    ) -> str | None:
        ext = os.path.basename(path).split('.')[-1]
        filename = f'{uuid.uuid4().hex}.{ext}'
        filepath = os.path.join(folder, filename)

        file_data = await self.get_file(bucket, path)
        if not file_data:
            logger.error(f"No file data: {path}")
            return None

        async with aiofiles.open(filepath, 'wb') as f:
            await f.write(file_data)
        return filepath

    async def get_file(
            self,
            bucket: str,
            path: str,
    ) -> bytes | None:
        try:
            async with self.get_client() as client:
                response = await client.get_object(
                    Bucket=bucket,
                    Key=path
                )
                return await response["Body"].read()
        except ClientError as e:
            logger.error(e)

    async def head_file(self, bucket: str, path: str) -> dict:
        try:
            async with self.get_client() as client:
                response = await client.head_object(
                    Bucket=bucket,
                    Key=path
                )
                return response
        except ClientError as e:
            logger.error(e)

    async def delete_file(self, bucket: str, path: str) -> None:
        try:
            async with self.get_client() as client:
                response = await client.delete_object(
                    Bucket=bucket,
                    Key=path
                )
                return response
        except ClientError as e:
            logger.error(e)
