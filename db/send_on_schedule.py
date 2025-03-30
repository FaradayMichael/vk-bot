from sqlalchemy import select

from models import SendOnSchedule
from schemas.send_on_schedule import SendOnScheduleNew
from utils import db


async def create(
        session: db.Session,
        model: SendOnScheduleNew
) -> SendOnSchedule:
    obj = SendOnSchedule(**model.model_dump())
    session.add(obj)
    await session.commit()
    return obj


async def get_list(
        session: db.Session,
) -> list[SendOnSchedule]:
    stmt = select(SendOnSchedule).where(SendOnSchedule.en)
    result = await session.execute(stmt)
    return list(result.scalars().all())
