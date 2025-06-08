import datetime

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.vk_tasks import VkTask
from app.schemas.vk_tasks import (
    VkTask as VkTaskSchema
)


async def create(
        session: AsyncSession,
        model: VkTaskSchema
) -> VkTask:
    obj = VkTask(**model.model_dump())
    session.add(obj)
    await session.commit()
    return obj


async def get_list(
        session: AsyncSession,
        from_dt: datetime.datetime | None = None,
        to_dt: datetime.datetime | None = None,
        funcs_in: list[str] | None = None,
        uuid_in: list[str] | None = None
) -> list[VkTask]:
    where = []
    if from_dt:
        where.append(
            VkTask.ctime <= from_dt
        )
    if to_dt:
        where.append(
            VkTask.ctime <= to_dt
        )
    if funcs_in:
        where.append(
            VkTask.func.in_(funcs_in)
        )
    if uuid_in:
        where.append(
            VkTask.uuid.in_(uuid_in)
        )

    stmt = select(VkTask).where(
        and_(*where)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())
