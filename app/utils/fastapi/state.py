import asyncio

import aio_pika
from fastapi import FastAPI
from jinja2 import Environment

from app.services.utils.client import UtilsClient
from app.utils import redis, smtp
from app.utils.config import Config
from app.services.vk_bot.client import VkBotClient
from app.utils.db import DBHelper


class State:
    def __init__(
        self, loop: asyncio.BaseEventLoop | asyncio.AbstractEventLoop, config: Config
    ):
        self.loop: asyncio.BaseEventLoop = loop
        self.config: Config = config
        self.db_helper: DBHelper | None = None
        self.redis_pool: redis.Connection | None = None
        self.app: FastAPI | None = None
        self.smtp: smtp.SMTP | None = None
        self.jinja: Environment | None = None

        self.amqp: aio_pika.RobustConnection | aio_pika.Connection | None = None
        self.vk_bot_client: VkBotClient | None = None
        self.utils_client: UtilsClient | None = None
