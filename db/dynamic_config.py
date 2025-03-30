from sqlalchemy import (
    select,
    update as update_
)

from models import DynamicConfig
from utils import db


async def get(
        session: db.Session
) -> dict:
    stmt = select(DynamicConfig).limit(1)
    result = await session.execute(stmt)
    exist = result.scalars().first()
    if not exist:
        exist = DynamicConfig()
        session.add(exist)
        await session.commit()
    return exist.data


async def update(
        session: db.Session,
        data: dict,
        **update_data
) -> dict:
    data.update(update_data)
    stmt = update_(DynamicConfig).values(**data).returning(DynamicConfig)
    result = await session.execute(stmt)
    await session.commit()
    obj = result.scalars().first()
    return obj.data or {}
