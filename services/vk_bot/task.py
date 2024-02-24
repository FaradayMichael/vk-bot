import datetime
import logging
import uuid
from typing import Callable

from asyncpg import Pool
from vk_api.bot_longpoll import VkBotEvent

from db import tasks as tasks_db
from models.vk_tasks import VkTask

logger = logging.getLogger(__name__)


class Task:
    def __init__(
            self,
            method: Callable,
            *args,
            **kwargs
    ):
        self.tries: int = 0
        self.uuid: str = uuid.uuid4().hex
        self.method: Callable = method
        self.args: tuple = args
        self.kwargs: dict = kwargs
        self.errors: list[Exception] = []

        self.created: datetime.datetime = datetime.datetime.now()
        self.started: datetime.datetime | None = None
        self.done: datetime.datetime | None = None

    async def execute(self):
        self.tries += 1
        if self.started is None:
            self.started = datetime.datetime.now()
        return await self.method(*self.args, **self.kwargs)

    @property
    def dict(self) -> dict:
        def parse_args(args: tuple) -> dict:
            result = {}
            for i, arg in enumerate(args):
                if isinstance(arg, VkBotEvent):
                    item = dict(arg.raw)
                elif isinstance(arg, dict):
                    item = arg
                else:
                    item = f"{arg}"
                result[i] = item
            return result

        return {
            'uuid': self.uuid,
            'method': self.method.__name__,
            'args': parse_args(self.args),
            'kwargs': self.kwargs,
            'errors': str(self.errors) if self.errors else None,
            'tries': self.tries,
            'created': self.created,
            'started': self.started,
            'done': self.done,
        }

    @property
    def model(self) -> VkTask:
        return VkTask.model_validate(self.dict)