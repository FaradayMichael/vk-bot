import logging

from misc import db
from misc.db_tables import DBTables
from models.vk_tasks import VkTask

TABLE = DBTables.VK_TASKS


async def create(
        conn: db.Connection,
        task: VkTask
) -> VkTask:
    record = await db.create(conn, TABLE, task.model_dump())
    return db.record_to_model(VkTask, record)
