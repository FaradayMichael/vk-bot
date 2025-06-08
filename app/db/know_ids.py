from sqlalchemy import and_, select

from app.models import KnowId
from app.utils import db


async def get_list(
        session: db.Session,
) -> list[KnowId]:
    stmt = select(KnowId).where(KnowId.en)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_by_vk_id(
        session: db.Session,
        vk_id: int
) -> KnowId | None:
    stmt = select(KnowId).where(
        and_(KnowId.en, vk_id == KnowId.vk_id)
    ).limit(1)
    result = await session.execute(stmt)
    return result.scalar()