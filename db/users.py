from sqlalchemy import (
    select,
    or_,
    and_,
)
from sqlalchemy.ext.asyncio import AsyncSession

from models import User
from schemas.auth import RegisterModel


async def create(
        session: AsyncSession,
        model: RegisterModel,
        hashed_password: str
) -> User:
    obj = User(
        password=hashed_password,
        **model.model_dump()
    )
    session.add(obj)
    await session.commit()
    return obj


async def get(
        session: AsyncSession,
        pk: int
) -> User | None:
    return await session.get(User, pk)


async def get_by_credentials(
        session: AsyncSession,
        username_or_email: str,
        password: str,
) -> User | None:
    stmt = select(User).where(
        and_(
            or_(User.username == username_or_email, User.email == username_or_email),
            User.password == password
        )
    )
    result = await session.scalars(stmt)
    return result.first()


async def email_exists(
        session: AsyncSession,
        email: str,
) -> bool:
    stmt = select(User).where(email == User.email)
    result = await session.execute(stmt)
    return result.scalars().first() is not None


async def login_exists(
        session: AsyncSession,
        username: str,
) -> bool:
    stmt = select(User).where(username == User.username)
    result = await session.execute(stmt)
    return result.scalars().first() is not None


async def set_password(
        session: AsyncSession,
        user: User,
        hashed_password: str
) -> User:
    user.password = hashed_password
    await session.commit()
    return user
