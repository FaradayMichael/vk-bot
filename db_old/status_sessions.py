import datetime

import asyncpg

from misc import (
    db
)
from utils import db_tables
from services.discord.models.activities import (
    StatusSessionCreate,
    StatusSessionUpdate,
    StatusSession
)

TABLE = db_tables.DBTables.DISCORD_STATUS_SESSIONS


async def create(
        conn: asyncpg.Pool | asyncpg.Connection,
        model: StatusSessionCreate
) -> StatusSession:
    record = await db.create(conn, TABLE, model.model_dump())
    return db.record_to_model(StatusSession, record)


async def get_list(
        conn: asyncpg.Connection | asyncpg.Pool,
        user_id: int | None = None,
        user_name: str | None = None,
        from_dt: datetime.datetime | None = None,
        to_dt: datetime.datetime | None = None,
        with_tz: datetime.tzinfo | None = None,
        unfinished: bool | None = None,
) -> list[StatusSession]:
    where = []
    values = []
    idx = 1
    if user_id:
        where.append(f"user_id = ${idx}")
        values.append(user_id)
        idx += 1
    if user_name:
        where.append(f"user_name = ${idx}")
        values.append(user_name)
        idx += 1
    if from_dt:
        where.append(f"started_at >= ${idx}")
        values.append(from_dt)
        idx += 1
    if to_dt:
        where.append(f"(finished_at IS NULL OR finished_at <= ${idx})")
        values.append(to_dt)
        idx += 1
    if unfinished is not None:
        if unfinished:
            where.append("finished_at IS NULL")
        else:
            where.append("finished_at IS NOT NULL")

    select = ['*']
    if with_tz:
        select += [
            f"timezone('{with_tz.tzname(None)}', started_at) as started_at_tz",
            f"timezone('{with_tz.tzname(None)}', finished_at) as finished_at_tz"
        ]
    query = f"""
        SELECT 
            {', '.join(select)}
        FROM {TABLE} 
        """
    if where:
        query += f" WHERE {' AND '.join(where)}"
    records = await conn.fetch(query, *values)
    return db.record_to_model_list(StatusSession, records)


async def get_last(
        conn: asyncpg.Connection | asyncpg.Pool,
        user_id: int,
        status: str
) -> StatusSession | None:
    query = f"""
        SELECT * FROM {TABLE} 
        WHERE user_id = $1 AND status = $2 
        ORDER BY started_at DESC 
        LIMIT 1
    """
    record = await conn.fetchrow(query, user_id, status)
    return db.record_to_model(StatusSession, record)


async def update(
        conn: asyncpg.Connection | asyncpg.Pool,
        pk: int,
        model: StatusSessionUpdate
) -> StatusSession:
    record = await db.update(
        conn,
        TABLE,
        pk,
        model.model_dump(exclude_none=True)
    )
    return db.record_to_model(StatusSession, record)


async def delete(
        conn: asyncpg.Connection | asyncpg.Pool,
        pk: int
) -> StatusSession | None:
    record = await db.delete(conn, TABLE, pk)
    return db.record_to_model(StatusSession, record)

async def get_users_data(
        conn: asyncpg.Connection | asyncpg.Pool,
) -> list[tuple[int, str]]:
    query = f"""
        SELECT 
            user_id, user_name
        FROM {TABLE} 
        GROUP BY user_id, user_name
    """
    records = await conn.fetch(query)
    return [
        (r['user_id'], r['user_name']) for r in records
    ]
