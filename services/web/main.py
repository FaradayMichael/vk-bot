import asyncio
import logging
import os
from pathlib import Path

from fastapi import (
    FastAPI,
    Depends,
)
from starlette.staticfiles import StaticFiles

from misc import (
    db,
    ctrl,
    redis,
    smtp,
    config
)
from misc.config import Config
from misc.depends.session import (
    get as get_session
)
from misc.handlers import register_exception_handler
from models.base import ErrorResponse, UpdateErrorResponse
from .state import State

logger = logging.getLogger(__name__)


def factory():
    app = ctrl.main_with_parses(None, main)
    if not app:
        raise RuntimeError
    return app


def main(args, config: Config):
    loop = asyncio.get_event_loop()
    config_dict = config.model_dump()
    root_path = config_dict.get('rot_path', None)
    state = State(
        loop=loop,
        config=config
    )
    app = FastAPI(
        title='VK Bot',
        debug=config.debug,
        root_path=root_path,
        responses=responses(),
        dependencies=[Depends(get_session)],
    )

    app.state = state
    state.app = app
    check_folders(config)
    register_exception_handler(app)

    register_routers(app)
    register_startup(app)
    register_shutdown(app)

    static = StaticFiles(directory=config.folders.static)
    app.mount(config.static_url, static, name='static')

    return app


def register_startup(app):
    @app.on_event("startup")
    async def handler_startup():
        logger.info('Startup called')
        try:
            await startup(app)
            logger.info("REST API app startup executed")
        except:
            logger.exception('Startup crashed')


def register_shutdown(app):
    @app.on_event("shutdown")
    async def handler_shutdown():
        logger.info('Shutdown called')
        try:
            await shutdown(app)
            logger.info("REST API app shutdown executed")
        except:
            logger.exception('Shutdown crashed')


async def startup(app):
    state: State = app.state

    state.db_pool = await db.init(app.state.config.db)
    state.redis_pool = await redis.init(app.state.config.redis)
    state.smtp = await smtp.init(app.state.config.smtp)

    app = await startup_jinja(app)
    return app


async def shutdown(app):
    state: State = app.state
    if state.db_pool:
        await db.close(state.db_pool)
    state.db_pool = None
    if state.redis_pool:
        await redis.close(state.redis_pool)
    state.redis_pool = None


async def startup_jinja(app):
    from jinja2 import (
        Environment,
        ChoiceLoader,
        FileSystemLoader,
        select_autoescape
    )

    env = Environment(
        loader=ChoiceLoader([
            FileSystemLoader('templates')
        ]),
        autoescape=select_autoescape()
    )
    app.state.jinja = env
    return app


def register_routers(app):
    from . import routers
    return routers.register_routers(app)


def check_folders(conf):
    # if not os.path.exists(config.static_files_folder(conf)):
    #     os.makedirs(config.static_files_folder(conf))
    if not os.path.exists(config.template_files_folder(conf)):
        os.makedirs(config.template_files_folder(conf))
    if not os.path.exists(config.static_files_folder(conf)):
        os.makedirs(config.static_files_folder(conf))


def responses():
    return {
        409: {
            "model": UpdateErrorResponse
        },
        400: {
            "model": ErrorResponse
        },
        401: {
            "model": ErrorResponse
        },
        404: {
            "model": ErrorResponse
        },
        422: {
            "model": ErrorResponse
        },
        500: {
            "model": ErrorResponse
        },
    }
