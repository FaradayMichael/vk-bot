import datetime

from sqlalchemy import (
    select,
    and_,
    or_,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.steam import (
    SteamUser,
    SteamActivitySession,
    SteamStatusSession,
)


async def get_users(session: AsyncSession) -> list[SteamUser]:
    stmt = select(SteamUser)
    result = await session.scalars(stmt)
    return list(result.all())


async def get_current_activity(
        session: AsyncSession,
        user_id: int
) -> SteamActivitySession | None:
    stmt = select(SteamActivitySession).where(
        and_(
            SteamActivitySession.user_id == user_id,
            SteamActivitySession.finished_at.is_(None)
        )
    )
    result = await session.scalars(stmt)
    if result:
        return result.first()


async def get_current_status(
        session: AsyncSession,
        user_id: int
) -> SteamStatusSession | None:
    stmt = select(SteamStatusSession).where(
        and_(
            SteamStatusSession.user_id == user_id,
            SteamStatusSession.finished_at.is_(None)
        )
    )
    result = await session.scalars(stmt)
    if result:
        return result.first()


async def get_users_data(
        session: AsyncSession
) -> list:
    stmt = select(
        SteamActivitySession.user_id.label("user_id"), SteamUser.username
    ).join(SteamUser).group_by(
        SteamActivitySession.user_id, SteamUser.username
    ).union(
        select(SteamStatusSession.user_id.label("user_id"), SteamUser.username).join(SteamUser).group_by(
            SteamStatusSession.user_id, SteamUser.username
        ),
    )
    result = await session.execute(stmt)
    return list(result.tuples())


async def get_list_activities(
        session: AsyncSession,
        user_id: int | None = None,
        from_dt: datetime.datetime | None = None,
        to_dt: datetime.datetime | None = None,
) -> list[SteamActivitySession]:
    where_stmts = []
    if user_id:
        user_id = user_id
        where_stmts.append(SteamActivitySession.user_id == user_id)
    if from_dt:
        where_stmts.append(SteamActivitySession.started_at >= from_dt)
    if to_dt:
        where_stmts.append(
            or_(SteamActivitySession.finished_at is None, SteamActivitySession.started_at <= to_dt)
        )

    stmt = select(SteamActivitySession).where(and_(*where_stmts))
    result = await session.scalars(stmt)
    return list(result.all())


async def get_list_statuses(
        session: AsyncSession,
        user_id: int | None = None,
        from_dt: datetime.datetime | None = None,
        to_dt: datetime.datetime | None = None,
) -> list[SteamStatusSession]:
    where_stmts = []
    if user_id:
        user_id = user_id
        where_stmts.append(SteamStatusSession.user_id == user_id)
    if from_dt:
        where_stmts.append(SteamStatusSession.started_at >= from_dt)
    if to_dt:
        where_stmts.append(
            or_(SteamStatusSession.finished_at is None, SteamStatusSession.started_at <= to_dt)
        )

    stmt = select(SteamStatusSession).where(and_(*where_stmts))
    result = await session.scalars(stmt)
    return list(result.all())
