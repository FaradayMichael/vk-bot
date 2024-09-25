import asyncpg

from misc import db
from misc.db_tables import DBTables
from services.discord.models.reply_commands import (
    ReplyCommand
)

TABLE = DBTables.DISCORD_REPLY_COMMANDS


async def get(
        conn: asyncpg.Connection | asyncpg.Pool,
        command: str
) -> ReplyCommand | None:
    record = await db.get_by_where(conn, TABLE, where='command = $1', values=[command])
    return db.record_to_model(ReplyCommand, record)


async def get_all(conn: asyncpg.Connection | asyncpg.Pool) -> list[ReplyCommand]:
    records = await db.get_list(
        conn,
        TABLE,
        where='en',
    )
    return db.record_to_model_list(ReplyCommand, records)
