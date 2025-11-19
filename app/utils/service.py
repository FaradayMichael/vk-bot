import asyncio
import inspect
import logging
from typing import (
    Awaitable,
    Callable,
    Any,
)

import aio_pika

from app.utils.config import (
    Config,
)

logger = logging.getLogger(__name__)

OnCloseCallback = Callable[[], Awaitable[None] | Any]


class BaseService:
    @classmethod
    async def create(
        cls,
        config: Config,
        controller_name: str,
        loop: asyncio.AbstractEventLoop,
        **kwargs,
    ) -> "BaseService":
        instance = cls(config, controller_name, loop, **kwargs)
        await instance.setup()
        return instance

    def __init__(
        self,
        config: Config,
        controller_name: str,
        loop: asyncio.AbstractEventLoop,
        **kwargs,
    ):
        super().__init__()
        self.config = config
        self.loop = loop
        self.controller_name = controller_name
        self.stopping: bool = False
        self.amqp: aio_pika.Connection | None = None
        self.on_closed: list[OnCloseCallback] = []

    async def setup(self):
        try:
            self.amqp = await asyncio.wait_for(
                aio_pika.connect_robust(
                    str(self.config.amqp), loop=self.loop, timeout=300
                ),
                timeout=30,
            )

            await self.init()
            logger.info(f"Service {self.controller_name} started")
        except TimeoutError:
            logger.exception("RabbitMQ connection timed out. Exiting service")
            self.stop()
        except Exception as exc:
            logger.exception(f"Service {self.controller_name} crashed with {exc}")
            self.stop()

    async def init(self):
        raise NotImplementedError()

    def register_on_closed(self, callback: OnCloseCallback):
        self.on_closed.append(callback)

    def stop(self):
        if not self.stopping:
            logger.info(f"Service {self.controller_name} stopping was planned")
            self.stopping = True

            self.loop.create_task(self.safe_close())

    async def safe_close(self):
        try:
            await self.close()
        except Exception as e:
            logger.error(f"Closed with exception: {e}")

    async def close(self):
        if self.amqp:
            await self.amqp.close()
        self.amqp = None

        for on_closed in self.on_closed:
            if inspect.isawaitable(on_closed):
                await on_closed()  # noqa
            else:
                on_closed()

        logger.info(f"Service {self.controller_name} was stopped successfully")
