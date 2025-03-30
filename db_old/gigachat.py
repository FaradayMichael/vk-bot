import asyncpg
from gigachat.models import Messages

from misc import db
from utils import db_tables

TABLE = db_tables.DBTables.GIGACHAT_MESSAGES


async def create(
        conn: asyncpg.Connection | asyncpg.Pool,
        user_id: str,
        model: Messages
) -> Messages:
    data = model.dict()
    data['user_id'] = user_id
    record = await db.create(conn, TABLE, data)
    return Messages.parse_obj(record)


async def get_by_user(
        conn: asyncpg.Connection | asyncpg.Pool,
        user_id: str,
) -> list[Messages]:
    records = await db.get_list(
        conn=conn,
        table=TABLE,
        where=f"user_id = $1",
        values=[user_id]
    )
    return [Messages.parse_obj(r) for r in records]


async def delete_by_user(
        conn: asyncpg.Connection | asyncpg.Pool,
        user_id: str,
) -> list[Messages]:
    records = await db.delete_by_where(
        conn=conn,
        table=TABLE,
        where=f"user_id = $1",
        values=[user_id],
        return_rows=True
    )
    return [Messages.parse_obj(r) for r in records]
