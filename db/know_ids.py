from misc import db
from misc.db_tables import DBTables
from models.know_ids import KnowIds

TABLE = DBTables.KNOW_IDS


async def get(
        conn: db.Connection,
        pk: int
) -> KnowIds | None:
    return db.record_to_model(
        KnowIds,
        await db.get(conn, TABLE, pk)
    )


async def get_all(
        conn: db.Connection
) -> list[KnowIds]:
    record = await db.get_list(
        conn,
        TABLE
    )
    return db.record_to_model_list(KnowIds, record)
