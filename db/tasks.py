import datetime
import logging

from misc import db
from misc.db_tables import DBTables
from models.vk_tasks import (
    VkTask
)

TABLE = DBTables.VK_TASKS


async def create(
        conn: db.Connection,
        task: VkTask
) -> VkTask:
    record = await db.create(conn, TABLE, task.model_dump(exclude_none=True))
    return db.record_to_model(VkTask, record)


async def get_list(
        conn: db.Connection,
        from_dt: datetime.datetime | None = None,
        to_dt: datetime.datetime | None = None,
        methods_in: list[str] | None = None,
        uuid_in: list[str] | None = None
) -> list[VkTask]:
    where = []
    values = []
    idx = 1

    if from_dt is not None:
        where.append(f"ctime >= ${idx}")
        values.append(from_dt)
        idx += 1
    if to_dt:
        where.append(f"ctime <= ${idx}")
        values.append(to_dt)
        idx += 1
    if methods_in is not None:
        where.append(f"method = ANY (${idx})")
        values.append(methods_in)
        idx += 1
    if uuid_in:
        where.append(f"uuid = ANY (${idx})")
        values.append(uuid_in)
        idx += 1

    records = await db.get_by_where(
        conn=conn,
        table=TABLE,
        where=' AND '.join(where),
        values=values,
        return_rows=True
    )
    return db.record_to_model_list(VkTask, records)
