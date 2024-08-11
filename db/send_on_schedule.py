import asyncpg

from misc import db, db_tables
from models.send_on_schedule import (
    SendOnSchedule,
    SendOnScheduleNew
)

TABLE = db_tables.DBTables.SEND_ON_SCHEDULE


async def create(
        conn: db.Connection,
        model: SendOnScheduleNew
) -> SendOnSchedule:
    record = await db.create(conn, TABLE, model.model_dump())
    return db.record_to_model(SendOnSchedule, record)


async def get_list(
        conn: db.Connection | asyncpg.Pool
) -> list[SendOnSchedule]:
    records = await db.get_list(
        conn=conn,
        table=TABLE,
        where="en"
    )
    return db.record_to_model_list(SendOnSchedule, records)
