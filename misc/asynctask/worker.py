import asyncio
import logging
import socket
import time
from typing import (
    Awaitable,
    Type,
    Callable,
)

import aio_pika
from aio_pika.abc import (
    ConsumerTag,
    AbstractRobustConnection,
)
from pydantic import BaseModel

from .serializer import (
    Serializer,
)
from .models import (
    METHOD_HEADER,
    ErrorData,
    ExceptionData,
    ExceptionType,
    MessageType,
    ModelClass,
)

logger = logging.getLogger(__name__)

QUEUE_NAME = 'tasks'

HandlerCallback = Callable[['Context'], Awaitable[None]]


class Handler:
    def __init__(self, method: str, handler: HandlerCallback, model_class: Type[ModelClass]):
        self.method = method
        self.handler = handler
        self.model_class = model_class

    async def handle(self, context: 'Context'):
        await self.handler(context)


class Context:
    def __init__(self, incoming_message: aio_pika.IncomingMessage, data: ModelClass, worker: 'Worker'):
        self.incoming_message = incoming_message
        self.data = data
        self.worker = worker
        self.replied: bool = False
        self.lock: asyncio.Lock = asyncio.Lock()

    async def success(self, data: ModelClass | None = None):
        await self.reply_to(
            data=data,
            t=MessageType.SUCCESS
        )

    async def canceled(self):
        await self.reply_to(
            data=b'',  # noqa
            t=MessageType.CANCELED
        )

    async def exception(self, data: ExceptionData):
        await self.reply_to(
            data=data,
            t=MessageType.EXCEPTION
        )

    async def error(self, data: ErrorData):
        await self.reply_to(
            data=data,
            t=MessageType.ERROR
        )

    async def reply_to(self, data: ModelClass, t: MessageType):
        async with self.lock:
            if not self.replied:
                self.replied = True
                await self.worker.reply_to(
                    incoming_message=self.incoming_message,
                    data=data,
                    t=t
                )


class Worker:
    @classmethod
    async def create(
            cls,
            conn: aio_pika.RobustConnection | aio_pika.Connection | AbstractRobustConnection,
            queue_name: str,
            serializer: Serializer,
            prefetch_count: int = 1,
            enable_reply: bool = True,
    ) -> 'Worker':
        instance = cls(conn, queue_name, serializer, prefetch_count, enable_reply)
        await instance.init()
        return instance

    def __init__(
            self,
            conn: aio_pika.RobustConnection | aio_pika.Connection,
            queue_name: str,
            serializer: Serializer,
            prefetch_count: int = 1,
            enable_reply: bool = True,
    ):
        super().__init__()
        self.conn = conn
        self.queue_name = queue_name
        self.serializer = serializer
        self.prefetch_count = prefetch_count
        self.enable_reply = enable_reply
        self.channel: aio_pika.RobustChannel | None = None
        self.queue: aio_pika.RobustQueue | None = None
        self.handlers: dict[str, Handler] = {}
        self.consumer_tag: ConsumerTag | None = None
        self.lock: asyncio.Lock = asyncio.Lock()

    async def init(self):
        self.channel = await self.conn.channel()
        await self.channel.set_qos(prefetch_count=self.prefetch_count)

        self.queue = await self.channel.declare_queue(
            name=self.queue_name,
            auto_delete=False,
        )

        self.consumer_tag = await self.queue.consume(
            self.on_message,
            no_ack=False,
        )

        logger.info(f'Worker initialised for queue {self.queue_name}')

    async def close(self):
        # async with self.lock:
        if self.consumer_tag:
            await self.queue.cancel(self.consumer_tag)
        self.consumer_tag = None

        self.queue = None

        if self.channel:
            await self.channel.close()
        logger.info(f'Worker for queue {self.queue_name} closed')

    def register(self, method: str, handler: HandlerCallback, model_class: Type[BaseModel]):
        self.handlers[method] = Handler(
            method=method,
            handler=handler,
            model_class=model_class,
        )
        logger.info(f'Handler {method}[{model_class.__name__ if model_class else "None"}] registered')

    async def on_message(
            self,
            incoming_message: aio_pika.IncomingMessage | aio_pika.abc.AbstractIncomingMessage
    ):
        try:
            if not self.queue:
                await incoming_message.reject(requeue=True)
                return

            await self.handle(incoming_message)
        except (GeneratorExit, asyncio.CancelledError):
            await self.reply_to(
                incoming_message=incoming_message,
                t=MessageType.CANCELED,
            )
        except Exception as exc:
            logger.exception(
                f'Message {incoming_message} handled with exception')
            await self.reply_to(
                incoming_message=incoming_message,
                t=MessageType.EXCEPTION,
                data=ExceptionData(
                    cls=exc.__class__.__name__,
                    message=str(exc),
                    t=ExceptionType.UNKNOWN,
                )
            )
        finally:
            try:
                await incoming_message.ack()
            except Exception:
                logger.exception(f"Error asking message {incoming_message.body.decode()}")
                raise

    async def handle(self, incoming_message: aio_pika.IncomingMessage):
        method = incoming_message.headers.get(METHOD_HEADER, None)
        if not method:
            await self.reply_to(
                incoming_message=incoming_message,
                t=MessageType.NO_HANDLER,
                data=ErrorData(
                    message=f'Method not found at message'
                )
            )
            return

        handler = self.handlers.get(method, None)
        if not handler:
            await self.reply_to(
                incoming_message=incoming_message,
                t=MessageType.NO_HANDLER,
                data=ErrorData(
                    message=f'Handler {method} not found'
                )
            )
            return

        await handler.handle(
            context=Context(
                incoming_message=incoming_message,
                data=self.serializer.unpack(
                    incoming_message.body, handler.model_class),
                worker=self,
            )
        )

    async def reply_to(
            self,
            incoming_message: aio_pika.IncomingMessage,
            t: MessageType,
            data: ModelClass | None = None
    ):
        if not self.enable_reply:
            return None

        body = self.serializer.pack(data)
        reply_message = aio_pika.Message(
            type=t.value,
            body=body,
            content_type=self.serializer.content_type(),
            correlation_id=incoming_message.correlation_id,
            delivery_mode=incoming_message.delivery_mode,
            timestamp=time.time(),
            app_id=socket.gethostname(),
        )
        await self.channel.default_exchange.publish(
            message=reply_message,
            routing_key=incoming_message.reply_to,
            mandatory=False,
        )
