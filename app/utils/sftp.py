import asyncio
import os
import uuid
from typing import Any

from paramiko import (
    Transport,
    SFTPClient
)

from app.utils.config import SftpConfig


class SftpClient:
    def __init__(
            self,
            config: SftpConfig
    ):
        self._config = config
        self._transport: Transport | None = None
        self.client: SFTPClient | None = None

    async def download(
            self,
            path: str,
            folder: str = 'static',
    ) -> str:
        ext = os.path.basename(path).split('.')[-1]
        filename = f'{uuid.uuid4().hex}.{ext}'
        filepath = os.path.join(folder, filename)

        # self.client.get(path, filepath)
        await asyncio.to_thread(
            self.client.get,
            path,
            filepath,
            None, True, None
        )
        return filepath

    async def stat(self, path: str) -> Any:
        return await asyncio.to_thread(
            self.client.stat,
            path
        )

    async def remove(self, path: str) -> None:
        self.client.remove(path)

    async def init(self):
        self._transport = Transport((self._config.host, self._config.port))
        self._transport.connect(username=self._config.username, password=self._config.password)
        self.client = SFTPClient.from_transport(self._transport)

    async def __aenter__(self):
        await self.init()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def close(self):
        if self.client:
            self.client.close()
            self.client = None
        if self._transport:
            self._transport.close()
            self._transport = None
