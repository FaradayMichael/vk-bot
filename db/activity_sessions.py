import datetime

import asyncpg

from misc import db
from misc.db_tables import DBTables
from services.discord.models import (
    ActivitySession,
    ActivitySessionCreate,
    ActivitySessionUpdate
)

TABLE = DBTables.DISCORD_ACTIVITY_SESSIONS


async def create(
        conn: asyncpg.Connection | asyncpg.Pool,
        model: ActivitySessionCreate
) -> ActivitySession:
    record = await db.create(conn, TABLE, model.model_dump())
    return db.record_to_model(ActivitySession, record)


async def update(
        conn: asyncpg.Connection | asyncpg.Pool,
        pk: int,
        model: ActivitySessionUpdate
) -> ActivitySession:
    record = await db.update(
        conn,
        TABLE,
        pk,
        model.model_dump(exclude_none=True)
    )
    return db.record_to_model(ActivitySession, record)


async def get_unfinished(
        conn: asyncpg.Connection | asyncpg.Pool,
        user_id: int,
        activity_name: str
) -> ActivitySession | None:
    query = f"""
        SELECT * FROM {TABLE} 
        WHERE user_id = $1 AND activity_name = $2 
        ORDER BY started_at DESC 
        LIMIT 1
    """
    record = await conn.fetchrow(query, user_id, activity_name)
    return db.record_to_model(ActivitySession, record)


async def get_all(
        conn: asyncpg.Connection | asyncpg.Pool,
        user_id: int | None = None,
        user_name: str | None = None,
        from_dt: datetime.datetime | None = None,
        to_dt: datetime.datetime | None = None,
) -> list[ActivitySession]:
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

    query = f"""
        SELECT * FROM {TABLE} 
        """
    if where:
        query += f" WHERE {' AND '.join(where)}"
    records = await conn.fetch(query, *values)
    return db.record_to_model_list(ActivitySession, records)


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
