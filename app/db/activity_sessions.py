import datetime

from sqlalchemy import (
    and_,
    or_,
    select,
    update as update_,
    delete as delete_,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.discord_activity_sessions import DiscordActivitySession
from app.services.discord.models.activities import ActivitySessionCreate, ActivitySessionUpdate


async def create(
        session: AsyncSession,
        model: ActivitySessionCreate
) -> DiscordActivitySession:
    obj = DiscordActivitySession(**model.model_dump())
    session.add(obj)
    await session.commit()
    return obj


async def update(
        session: AsyncSession,
        pk: int,
        model: ActivitySessionUpdate | None = None,
        **update_data
) -> DiscordActivitySession | None:
    data = {}
    if model:
        data = model.model_dump(exclude_none=True)
    data.update(update_data)

    stmt = update_(DiscordActivitySession).values(**data).where(pk == DiscordActivitySession.id).returning(
        DiscordActivitySession)
    result = await session.execute(stmt)
    await session.commit()
    return result.scalars().first()


async def delete(
        session: AsyncSession,
        pk: int,
) -> DiscordActivitySession | None:
    stmt = delete_(DiscordActivitySession).where(pk == DiscordActivitySession.id).returning(DiscordActivitySession)
    result = await session.execute(stmt)
    await session.commit()
    return result.scalars().first()


async def get_first_unfinished(
        session: AsyncSession,
        user_id: str | int,
        activity_name: str
) -> DiscordActivitySession | None:
    user_id = str(user_id)
    stmt = select(DiscordActivitySession).where(
        and_(user_id == DiscordActivitySession.user_id, activity_name == DiscordActivitySession.activity_name)
    ).order_by(DiscordActivitySession.started_at.desc()).limit(1)
    result = await session.execute(stmt)
    return result.scalars().first()


async def get_list(
        session: AsyncSession,
        user_id: str | None = None,
        user_name: str | None = None,
        from_dt: datetime.datetime | None = None,
        to_dt: datetime.datetime | None = None,
        unfinished: bool | None = None,
) -> list[DiscordActivitySession]:
    where_stmts = []
    if user_id:
        user_id = str(user_id)
        where_stmts.append(DiscordActivitySession.user_id == user_id)
    if user_name:
        where_stmts.append(DiscordActivitySession.user_name == user_name)
    if from_dt:
        where_stmts.append(DiscordActivitySession.started_at >= from_dt)
    if to_dt:
        where_stmts.append(
            or_(DiscordActivitySession.finished_at is None, DiscordActivitySession.started_at <= to_dt)
        )
    if unfinished is not None:
        if unfinished:
            where_stmts.append(DiscordActivitySession.finished_at is None)
        else:
            where_stmts.extend(DiscordActivitySession.finished_at is not None)

    stmt = select(DiscordActivitySession).where(and_(*where_stmts))
    result = await session.scalars(stmt)
    return list(result.all())


async def get_users_data(
        session: AsyncSession,
) -> list[tuple[str, str]]:
    stmt = select(
        DiscordActivitySession.user_id, DiscordActivitySession.user_name
    ).group_by(
        DiscordActivitySession.user_id, DiscordActivitySession.user_name
    )
    result = await session.execute(stmt)
    return list(result.tuples())
