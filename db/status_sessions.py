import datetime

from sqlalchemy import (
    and_,
    or_,
    select,
    update as update_,
    delete as delete_,
)
from sqlalchemy.ext.asyncio import AsyncSession

from models.discord_status_sessions import DiscordStatusSession
from services.discord.models.activities import (
    StatusSessionUpdate,
    StatusSessionCreate
)


async def create(
        session: AsyncSession,
        model: StatusSessionCreate
) -> DiscordStatusSession:
    obj = DiscordStatusSession(**model.model_dump())
    session.add(obj)
    await session.commit()
    return obj


async def update(
        session: AsyncSession,
        pk: int,
        model: StatusSessionUpdate | None = None,
        **update_data
) -> DiscordStatusSession | None:
    data = {}
    if model:
        data = model.model_dump(exclude_none=True)
    data.update(update_data)

    stmt = update_(DiscordStatusSession).values(**data).where(pk == DiscordStatusSession.id).returning(
        DiscordStatusSession)
    result = await session.execute(stmt)
    await session.commit()
    return result.scalars().first()



async def delete(
        session: AsyncSession,
        pk: int,
) -> DiscordStatusSession | None:
    stmt = delete_(DiscordStatusSession).where(pk == DiscordStatusSession.id).returning(DiscordStatusSession)
    result = await session.execute(stmt)
    await session.commit()
    return result.scalars().first()


async def get_list(
        session: AsyncSession,
        user_id: str | None = None,
        user_name: str | None = None,
        from_dt: datetime.datetime | None = None,
        to_dt: datetime.datetime | None = None,
        unfinished: bool | None = None,
) -> list[DiscordStatusSession]:
    where_stmts = []
    if user_id:
        where_stmts.append(DiscordStatusSession.user_id == user_id)
    if user_name:
        where_stmts.append(user_name == DiscordStatusSession.user_name)
    if from_dt:
        where_stmts.append(DiscordStatusSession.started_at >= from_dt)
    if to_dt:
        where_stmts.append(
            or_(DiscordStatusSession.finished_at is None, DiscordStatusSession.started_at <= to_dt)
        )
    if unfinished is not None:
        if unfinished:
            where_stmts.append(DiscordStatusSession.finished_at is None)
        else:
            where_stmts.extend(DiscordStatusSession.finished_at is not None)

    stmt = select(DiscordStatusSession).where(and_(*where_stmts))
    result = await session.scalars(stmt)
    return list(result.all())


async def get_first_unfinished(
        session: AsyncSession,
        user_id: str | int,
        status: str
) -> DiscordStatusSession | None:
    user_id = str(user_id)
    stmt = select(DiscordStatusSession).where(
        and_(user_id == DiscordStatusSession.user_id, status == DiscordStatusSession.status)
    ).order_by(DiscordStatusSession.started_at.desc()).limit(1)
    result = await session.execute(stmt)
    return result.scalars().first()


async def get_users_data(
        session: AsyncSession,
) -> list[tuple[str, str]]:
    stmt = select(
        DiscordStatusSession.user_id, DiscordStatusSession.user_name
    ).group_by(
        DiscordStatusSession.user_id, DiscordStatusSession.user_name
    )
    result = await session.execute(stmt)
    return list(result.tuples())
