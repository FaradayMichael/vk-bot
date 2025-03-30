from sqlalchemy import select

from models import KnowId
from utils import db


async def get_list(
        session: db.Session,
) -> list[KnowId]:
    stmt = select(KnowId).where(KnowId.en)
    result = await session.execute(stmt)
    return list(result.scalars().all())
