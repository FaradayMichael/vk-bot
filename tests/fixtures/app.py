import asyncio

from async_asgi_testclient import TestClient
from asyncpg import Pool
import pytest
from asgi_lifespan import LifespanManager
from httpx import AsyncClient

from misc import (
    db
)
from utils import config, env
from utils.ctrl import CONFIG_ENV_KEY
from utils.dataurl import DataURL
from utils.db_tables import DBTables
from services.rest_api.main import factory


@pytest.fixture(scope='session')
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope='session')
async def rest_api_app(event_loop):
    instance = factory()
    async with LifespanManager(instance):
        yield instance


@pytest.fixture(scope='session')
async def rest_api_client(rest_api_app) -> TestClient:
    async with AsyncClient(app=rest_api_app, base_url="http://localhost:8010") as client:
        yield client
    # return TestClient(rest_api_app)


@pytest.fixture(scope="session")
async def db_pool(rest_api_app) -> Pool:
    db_pool = rest_api_app.state.db_pool
    await reset_db(db_pool)
    yield db_pool


@pytest.fixture(scope="session")
async def conf() -> config.Config:
    config_path = env.get(CONFIG_ENV_KEY, strict=True)
    return config.read_config(config_path)


async def reset_db(db_pool: db.Connection):
    for table in DBTables:
        await db_pool.execute(f'TRUNCATE {table} CASCADE')


async def reset_table(table: str, db_pool):
    await db_pool.execute(f'TRUNCATE {table} CASCADE')


async def get_dummy_dataurl(path: str) -> DataURL:
    return DataURL.from_file(path, base64=True)
