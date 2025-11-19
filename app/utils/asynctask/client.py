import asyncio
import logging
import socket
import time
import uuid
import functools
from typing import (
    Any,
    Type,
)

from aio_pika import (
    RobustQueue,
    RobustConnection,
    RobustChannel,
    Message,
    DeliveryMode,
    IncomingMessage,
)
from aio_pika.message import ReturnedMessage
from aio_pika.abc import ConsumerTag, AbstractQueueIterator, AbstractIncomingMessage
from aiormq.abc import ExceptionType

from .serializer import (
    Serializer,
)
from .models import (
    METHOD_HEADER,
    ErrorData,
    ModelClass,
    MessageType,
    ExceptionData,
)
from .exceptions import (
    TaskCanceled,
    TaskError,
    TaskException,
    TaskReturned,
    TaskNoHandler,
)

logger = logging.getLogger(__name__)


class Task:
    def __init__(
        self,
        method: str,
        data: bytes,
        response_class: Type[ModelClass],
        priority: int | None = None,
        nullable_response: bool = False,
    ):
        self.id = uuid.uuid4().hex
        self.method = method
        self.data = data
        self.priority = priority
        self.response_class = response_class
        self.nullable_response = nullable_response
        self.future: asyncio.Future = asyncio.get_running_loop().create_future()

    def done(self):
        return self.future.done()

    def set_result(self, data):
        if not self.done():
            self.future.set_result(data)

    def set_exception(self, exc):
        if not self.done():
            self.future.set_exception(exc)

    def cancel(self, msg=None):
        self.future.cancel(msg)


class Client:
    @classmethod
    async def create(
        cls, conn: RobustConnection, worker_queue_name: str, serializer: Serializer
    ) -> "Client":
        instance = cls(conn, worker_queue_name, serializer)
        await instance.init()
        return instance

    def __init__(
        self, conn: RobustConnection, worker_queue_name: str, serializer: Serializer
    ):
        super().__init__()
        self.conn = conn
        self.client_queue_name = f"asynctask.clients.{uuid.uuid4().hex}"
        self.worker_queue_name = worker_queue_name
        self.serializer = serializer
        self.channel: RobustChannel | None = None
        self.queue: RobustQueue | None = None
        self.queue_iterator: AbstractQueueIterator | None = None
        self.tasks: dict[str, Task] = {}
        self.consumer_tag: ConsumerTag | None = None

    async def init(self):
        self.channel = await self.conn.channel()

        self.queue = await self.channel.declare_queue(
            name=self.client_queue_name,
            auto_delete=True,
        )

        self.consumer_tag = await self.queue.consume(
            self.on_message,
            no_ack=False,
        )

        self.channel.close_callbacks.add(self.on_close)
        self.channel.return_callbacks.add(self.on_message_returned)
        logger.info(f"Client initialised for queue {self.worker_queue_name}")

    async def close(self):
        for task in self.tasks.values():
            task.cancel()
        if self.tasks:
            await asyncio.wait([i.future for i in self.tasks.values()])
        self.tasks = {}

        if self.consumer_tag:
            await self.queue.cancel(self.consumer_tag)
        self.consumer_tag = None

        if self.queue:
            await self.queue.delete(if_unused=False, if_empty=False)
        self.queue = None

        if self.channel:
            await self.channel.close()
        logger.info(f"Client for queue {self.worker_queue_name} closed")

    async def call(
        self,
        method: str,
        data: ModelClass | None = None,
        response_class: Type[ModelClass] | None = None,
        priority: int | None = None,
        expiration: int | None = None,
        nullable_response: bool = False,
    ) -> Any:
        task = Task(
            method=method,
            data=data,
            response_class=response_class,
            priority=priority,
            nullable_response=nullable_response,
        )
        self.tasks[task.id] = task

        message = Message(
            body=self.serializer.pack(data),
            content_type=self.serializer.content_type(),
            type=MessageType.REQUEST.value,
            headers={METHOD_HEADER: method},
            timestamp=time.time(),
            priority=task.priority,
            correlation_id=task.id,
            delivery_mode=DeliveryMode.NOT_PERSISTENT,
            reply_to=self.queue.name,
            app_id=socket.gethostname(),
            expiration=expiration,
        )

        await self.channel.default_exchange.publish(
            message,
            routing_key=self.worker_queue_name,
            mandatory=True,
        )

        return await asyncio.wait_for(task.future, timeout=expiration)

    async def on_message(
        self, incoming_message: IncomingMessage | AbstractIncomingMessage
    ):
        task = self.tasks.pop(incoming_message.correlation_id, None)
        if not task:
            logger.error(
                f"Task {incoming_message.correlation_id} for message {incoming_message} not found"
            )
            await incoming_message.ack()
            return

        try:
            if incoming_message.type == MessageType.SUCCESS:
                if task.nullable_response and not incoming_message.body:
                    task.set_result(None)
                else:
                    data = self.serializer.unpack(
                        incoming_message.body, task.response_class
                    )
                    task.set_result(data)
            elif incoming_message.type == MessageType.CANCELED:
                task.set_exception(TaskCanceled())
            elif incoming_message.type == MessageType.ERROR:
                task.set_exception(
                    TaskError(
                        self.serializer.unpack(incoming_message.body, ErrorData).message
                    )
                )
            elif incoming_message.type == MessageType.EXCEPTION:
                task.set_exception(
                    TaskException(
                        self.serializer.unpack(incoming_message.body, ExceptionData)
                    )
                )
            elif incoming_message.type == MessageType.NO_HANDLER:
                task.set_exception(
                    TaskNoHandler(
                        self.serializer.unpack(incoming_message.body, ErrorData).message
                    )
                )
            else:
                task.set_exception(
                    RuntimeError(
                        f"Unknown response {incoming_message.type} {incoming_message.body}"
                    )
                )
        except Exception as exc:
            task.set_exception(exc)
        finally:
            try:
                await incoming_message.ack()
            except Exception:
                logger.exception(
                    f"Error asking message {incoming_message.body.decode()}"
                )
                raise

    def on_close(
        self,
        exc: ExceptionType | None = None,
    ) -> None:
        for task in self.tasks.values():
            if not task.done():
                if exc:
                    task.set_exception(exc)
                else:
                    task.cancel()

    def on_message_returned(self, returned_message: ReturnedMessage):
        logger.error("Message returned")
        task = self.tasks.pop(returned_message.correlation_id, None)
        if task:
            if not task.done():
                task.set_exception(TaskReturned(f"Task {task.id} message returned"))
        else:
            logger.error(f"Message returned {returned_message}")


IGNORE_EXCEPTIONS = [
    "Captcha",
    "ProxyBanned",
    "NetworkTrouble",
    "TooManyRequests",
    "PageNotFound",
    "InvalidSessionIdException",
    "RestartParser",
]


def retry(fn):
    @functools.wraps(fn)
    async def wrapper(*args, **kwargs):
        last_exception: Exception | None = None
        retries = 5
        while 1:
            try:
                return await fn(*args, **kwargs)
            except asyncio.CancelledError:
                raise
            except TaskReturned:
                logger.info(f"Waiting parser nodes to start")
            except (
                TaskCanceled,
                asyncio.TimeoutError,
                TimeoutError,
                TaskNoHandler,
            ) as exc:
                logger.info(f"pass {exc.cls}")
                pass
            except TaskException as exc:
                if exc.cls not in IGNORE_EXCEPTIONS:
                    retries -= 1
                    last_exception = exc
            except Exception as exc:
                retries -= 1
                last_exception = exc

            if retries < 1:
                break

            await asyncio.sleep(5)

        raise last_exception

    return wrapper
