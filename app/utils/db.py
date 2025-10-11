from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncEngine,
    AsyncSession
)

from app.utils.config import PostgresqlConfig

Session = AsyncSession


class DBHelper:
    def __init__(
            self,
            dsn: str,
    ):
        self._dsn = dsn
        self.engine: AsyncEngine | None = None
        self.session_maker: async_sessionmaker[Session] | None = None

    async def init(self):
        self.engine = create_async_engine(url=self._dsn)
        self.session_maker = async_sessionmaker(bind=self.engine)

    async def close(self):
        if self.engine:
            await self.engine.dispose(close=True)
            self.engine = None
            self.session_maker = None

    @asynccontextmanager
    async def get_session(self) -> Session:
        async with self.session_maker(expire_on_commit=False) as session:
            yield session
            # await session.close()


async def init_db(config: PostgresqlConfig) -> DBHelper:
    db_helper = DBHelper(config.dsn)
    await db_helper.init()
    return db_helper
