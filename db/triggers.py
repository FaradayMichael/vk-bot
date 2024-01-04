import asyncpg

from db import (
    answers as answers_db
)
from misc import db
from misc.db_tables import DBTables
from models.triggers import (
    Trigger,
    TriggerCreate
)

TABLE = DBTables.TRIGGERS


async def create(
        conn: db.Connection,
        model: TriggerCreate
) -> Trigger:
    model.value = model.value.strip().lower()
    record = await db.create(conn, TABLE, model.model_dump())
    return await record_to_model(conn, record)


async def get_by_value(
        conn: db.Connection,
        value: str
) -> Trigger | None:
    record = await db.get_by_where(
        conn,
        TABLE,
        "value=$1",
        [value]
    )
    return await record_to_model(conn, record)


async def get_or_create(
        conn: db.Connection,
        value: str
) -> Trigger:
    result = await get_by_value(conn, value)
    if not result:
        result = await create(
            conn,
            TriggerCreate(value=value)
        )
    return result


async def get_list(
        conn: db.Connection,
        like: str
) -> list[Trigger]:
    records = await db.get_by_where(
        conn,
        TABLE,
        "LOWER(value) LIKE $1",
        [f"%{like.strip().lower()}%"],
        return_rows=True
    )
    return await record_to_model_list(conn, records)


async def record_to_model_list(
        conn: db.Connection,
        records: list[asyncpg.Record]
) -> list[Trigger]:
    return await db.record_to_model_list_custom(
        conn,
        records,
        record_to_model
    )


async def record_to_model(
        conn: db.Connection,
        record: asyncpg.Record | None
) -> Trigger | None:
    if not record:
        return None

    answers = await answers_db.get_by_trigger(conn, record['id'])

    return Trigger(
        **dict(record),
        answers=answers
    )
