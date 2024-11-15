import asyncio
from typing import (
    Optional,
)

import aio_pika
from fastapi import FastAPI

from misc import db, redis, smtp
from misc.config import Config
from services.vk_bot.client import VkBotClient


class State(object):
    def __init__(self, loop: asyncio.BaseEventLoop | asyncio.AbstractEventLoop, config: Config):
        super().__init__()
        self.loop: asyncio.BaseEventLoop = loop
        self.config: Config = config
        self.db_pool: Optional[db.Connection] = None
        self.redis_pool: Optional[redis.Connection] = None
        self.app: Optional[FastAPI] = None
        self.smtp: Optional[smtp.SMTP] = None

        self.amqp: aio_pika.RobustConnection | aio_pika.Connection | None = None
        self.vk_bot_client: VkBotClient | None = None
