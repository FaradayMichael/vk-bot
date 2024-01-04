from misc import db
from misc.db_tables import DBTables
from models.answers import (
    Answer,
    AnswerCreate
)

TABLE = DBTables.ANSWERS
TRIGGERS_ANSWERS_TABLE = DBTables.TRIGGERS_ANSWERS


async def create(
        conn: db.Connection,
        model: AnswerCreate
) -> Answer:
    model.value = model.value.strip().lower()
    record = await db.create(conn, TABLE, model.model_dump())
    return db.record_to_model(Answer, record)


async def get_by_value(
        conn: db.Connection,
        value: str
) -> Answer | None:
    record = await db.get_by_where(
        conn,
        TABLE,
        "value=$1",
        [value]
    )
    return db.record_to_model(Answer, record)


async def get_or_create(
        conn: db.Connection,
        value: str
) -> Answer:
    result = await get_by_value(conn, value)
    if not result:
        result = await create(
            conn,
            AnswerCreate(value=value)
        )
    return result


async def get_by_trigger(
        conn: db.Connection,
        trigger_id: int
) -> list[Answer]:
    ids_query = f"""
        SELECT answer_id FROM {TRIGGERS_ANSWERS_TABLE.value} 
        WHERE trigger_id=$1
    """
    records = await db.get_by_where(
        conn,
        TABLE,
        f"id = ANY ({ids_query})",
        [trigger_id],
        return_rows=True
    )
    return db.record_to_model_list(Answer, records)
