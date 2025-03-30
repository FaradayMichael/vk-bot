from datetime import datetime

from sqlalchemy import select, and_

from models import VkTask
from utils import db


async def get_list(
        session: db.Session,
        from_dt: datetime | None = None,
        to_dt: datetime | None = None,
        funcs_in: list[str] | None = None
) -> list[VkTask]:
    where = []
    if from_dt:
        where.append(VkTask.ctime >= from_dt)
    if to_dt:
        where.append(VkTask.ctime <= to_dt)
    if funcs_in:
        where.append(VkTask.func.in_(funcs_in))

    stmt = select(VkTask).where(
        and_(*where)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())
