import asyncpg

from misc import db
from misc.db_tables import DBTables

TABLE = DBTables.DYNAMIC_CONFIG


async def get(conn: asyncpg.Pool | asyncpg.Connection) -> dict:
    record = await db.get(conn, TABLE, 1)
    return record.get('data', {}) if record else {}


async def update(conn: asyncpg.Pool | asyncpg.Connection, data: dict) -> dict:
    record = await db.update(
        conn,
        TABLE,
        1,
        {
            'data': data
        }
    )
    return record.get('data', {}) if record else {}
