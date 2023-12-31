import asyncpg

from misc import db
from misc.db_tables import DBTables
from models.triggers_answers import (
    TriggerAnswerCreate,
    TriggerAnswer,
    TriggerGroup
)

TABLE = DBTables.TRIGGERS_ANSWERS


async def create(
        conn: db.Connection,
        model: TriggerAnswerCreate
) -> TriggerAnswer:
    record = await db.create(
        conn,
        TABLE,
        model.model_dump()
    )
    return db.record_to_model(TriggerAnswer, record)


async def get_list(
        conn: db.Connection,
        trigger_q: str = '',
        answer_q: str = ''
) -> list[TriggerAnswer]:
    records = await db.get_by_where(
        conn=conn,
        table=TABLE,
        where="lower(trigger) LIKE $1 AND lower(answer) LIKE $2",
        values=[f"%{trigger_q.strip().lower()}%", f"%{answer_q.strip().lower()}%"],
        return_rows=True
    )
    return db.record_to_model_list(TriggerAnswer, records)


async def get_triggers_group(
        conn: db.Connection,
        q: str = ''
) -> list[TriggerGroup]:
    query = f"""
        SELECT 
            trigger,
            array_agg(answer) as answers
        FROM {TABLE.value}
        WHERE lower(trigger) LIKE $1 
        GROUP BY trigger
    """
    records = await conn.fetch(query, f"%{q.strip().lower()}%")
    return db.record_to_model_list(TriggerGroup, records)


async def get_for_like(
        conn: db.Connection,
        q: str = ''
) -> list[TriggerGroup]:
    query = f"""
        SELECT 
            trigger,
            array_agg(answer) as answers
        FROM {TABLE.value}
        WHERE $1 LIKE '%' || lower(trigger) || '%'
        GROUP BY trigger
    """
    records = await conn.fetch(query, q.strip().lower())
    return db.record_to_model_list(TriggerGroup, records)
