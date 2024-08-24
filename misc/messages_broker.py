import asyncio
import logging
from enum import IntEnum
from typing import AsyncIterable, Any, Type

import aio_pika
from aiokafka import AIOKafkaConsumer, ConsumerRecord
from aiokafka.errors import KafkaError
from pydantic import ValidationError

from misc.asynctask.serializer import JsonSerializer
from misc.asynctask.worker import Worker, Context
from misc.config import Config
from models.messages_broker import MBMessage

logger = logging.getLogger(__name__)


class MBProvider(IntEnum):
    KAFKA = 0
    RABBITMQ = 1
    REDIS = 2


class BaseConsumer:
    def __init__(
            self,
            config: Config
    ):
        self.config: Config = config
        self._consumer: Any | None = None
        self.base_ex: Type[Exception] | None = None

    @classmethod
    async def create(cls, config: Config, provider: MBProvider) -> 'BaseConsumer':
        match provider:
            case MBProvider.KAFKA:
                inst_class = KafkaConsumer
            case MBProvider.RABBITMQ:
                inst_class = RabbitMQConsumer
            case _ as arg:
                raise ValueError(f"Messages Broker provider {arg} is not supported")
        instance = inst_class(config)
        await instance.init()
        return instance

    async def init(self):
        pass

    async def lister(self) -> AsyncIterable[MBMessage]:
        yield
        raise NotImplementedError()

    async def _close_consumer(self):
        raise NotImplementedError()

    async def close(self):
        if self._consumer:
            await self._close_consumer()
            self._consumer = None


class KafkaConsumer(BaseConsumer):
    def __init__(self, config: Config):
        super().__init__(config)
        self._consumer: AIOKafkaConsumer | None = None
        self.base_ex: Type[Exception] | None = KafkaError

    async def init(self):
        await super().init()
        self._consumer = AIOKafkaConsumer(
            *self.config.kafka.topics,
            bootstrap_servers=self.config.kafka.bootstrap_servers,
            retry_backoff_ms=30000
        )
        try:
            await self._consumer.start()
        except Exception as e:
            await self._close_consumer()
            raise e

    async def lister(self) -> AsyncIterable[MBMessage]:
        async for msg in self._consumer:
            msg: ConsumerRecord
            logger.info(f"{msg.key=} {msg.topic=}")
            try:
                yield MBMessage.model_validate_json(msg.value)
            except ValidationError as e:
                logger.error(f"Invalid kafka message value: {e}")
                continue

    async def _close_consumer(self):
        await self._consumer.stop()


class RabbitMQConsumer(BaseConsumer):

    def __init__(self, config: Config):
        super().__init__(config)
        self._consumer: Worker | None = None
        self.amqp: aio_pika.Connection | None = None
        self.queue: asyncio.Queue = asyncio.Queue()

    async def on_message(self, context: Context):
        await self.queue.put(context.data)

    async def init(self):
        await super().init()
        try:
            self.amqp = await asyncio.wait_for(
                aio_pika.connect_robust(
                    str(self.config.amqp),
                    timeout=300
                ),
                timeout=30
            )
            self._consumer = await Worker.create(
                conn=self.amqp,
                queue_name="vk_bot_post_queue",
                serializer=JsonSerializer(),
                enable_reply=False
            )
            self._consumer.register(
                'vk_bot_post',
                self.on_message,
                MBMessage
            )

        except Exception as e:
            await self._close_consumer()
            raise e

    async def lister(self) -> AsyncIterable[MBMessage]:
        while True:
            try:
                item = await self.queue.get()
                yield item
            except (GeneratorExit, asyncio.CancelledError, KeyboardInterrupt):
                break

    async def _close_consumer(self):
        if self._consumer:
            await self._consumer.close()
