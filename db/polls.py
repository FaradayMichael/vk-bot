from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from models import Poll
from schemas.polls import PollCreate


async def create(
        session: AsyncSession,
        model: PollCreate
) -> Poll:
    obj = Poll(**model.model_dump())
    session.add(obj)
    await session.commit()
    return obj


async def disable(
        session: AsyncSession,
        pk: int
) -> Poll | None:
    stmt = update(Poll).values(en=False).where(pk == Poll.id).returning(Poll)
    result = await session.execute(stmt)
    return result.scalars().first()
