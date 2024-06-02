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
