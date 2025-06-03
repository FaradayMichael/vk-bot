from misc import db
from utils import db_tables
from schemas.polls import (
    PollCreate,
    Poll,
    PollServices
)

TABLE = db_tables.DBTables.POLLS


async def create(
        conn: db.Connection | db.Pool,
        model: PollCreate
) -> Poll:
    record = await db.create(conn, TABLE, model.model_dump())
    return db.record_to_model(Poll, record)


async def get_by_id(
        conn: db.Connection,
        pk: int
) -> Poll | None:
    record = await db.get(conn, TABLE, pk)
    return db.record_to_model(Poll, record)


async def get(
        conn: db.Connection | db.Pool,
        key: str,
        service: PollServices | None = None,
) -> Poll:
    where = ['key = $1']
    values = [key]
    idx = 2
    if service:
        where.append(
            f"service = ${idx}"
        )
        values.append(service)
        idx += 1

    record = await db.get_by_where(
        conn=conn,
        table=TABLE,
        where=",".join(where),
        values=values,
    )
    return db.record_to_model(Poll, record)


async def disable(
        conn: db.Connection | db.Pool,
        pk: int
) -> Poll | None:
    record = await db.disable_by_where(
        conn=conn,
        table=TABLE,
        pk=pk,
        data={
            'en': True
        },
        with_dtime=True
    )
    return db.record_to_model(Poll, record)
