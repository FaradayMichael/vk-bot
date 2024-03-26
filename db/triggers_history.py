import asyncpg

from db import (
    know_ids as know_ids_db,
    triggers_answers as triggers_answers_db
)
from misc import db
from misc.db_tables import DBTables
from models.triggers_history import (
    TriggersHistoryNew,
    TriggersHistory
)

TABLE = DBTables.TRIGGERS_HISTORY


async def create(
        conn: db.Connection,
        model: TriggersHistoryNew
) -> TriggersHistory:
    record = await db.create(conn, TABLE, model.model_dump())
    return await _record_to_model(conn, record)


async def get(
        conn: db.Connection,
        pk: int
) -> TriggersHistory | None:
    record = await db.get(conn, TABLE, pk)
    return await _record_to_model(conn, record)


async def get_list(
        conn: db.Connection
) -> list[TriggersHistory]:
    records = await db.get_list(
        conn=conn,
        table=TABLE,
        order=['-ctime']
    )
    return await _record_to_model_list(conn, records)


async def _record_to_model_list(
        conn: db.Connection,
        records: list[asyncpg.Record]
) -> list[TriggersHistory]:
    return await db.record_to_model_list_custom(conn, records, _record_to_model)


async def _record_to_model(
        conn: db.Connection,
        record: asyncpg.Record | None
) -> TriggersHistory | None:
    if not record:
        return None

    know_id = await know_ids_db.get(conn, record.get('vk_id', 0))
    trigger_answer = await triggers_answers_db.get(conn, record.get('trigger_answer_id', 0))

    return TriggersHistory(
        know_id=know_id,
        trigger_answer=trigger_answer,
        **dict(record)
    )
