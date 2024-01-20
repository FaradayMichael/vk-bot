import asyncio
from typing import (
    Optional,
)

from fastapi import FastAPI
from jinja2 import Environment

from misc import db, redis, smtp
from misc.config import Config


class State(object):
    def __init__(self, loop: asyncio.BaseEventLoop | asyncio.AbstractEventLoop, config: Config):
        super().__init__()
        self.loop: asyncio.BaseEventLoop = loop
        self.config: Config = config
        self.db_pool: Optional[db.Connection] = None
        self.redis_pool: Optional[redis.Connection] = None
        self.app: Optional[FastAPI] = None
        self.smtp: Optional[smtp.SMTP] = None
        self.jinja: Optional[Environment] = None
