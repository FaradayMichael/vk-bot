from sqlalchemy import select

from app.models.discord_reply_commands import DiscordReplyCommand
from app.utils import db


async def get(
        session: db.Session,
        command: str
) -> DiscordReplyCommand | None:
    return await session.get(DiscordReplyCommand, command)


async def get_list(
        session: db.Session
) -> list[DiscordReplyCommand]:
    stmt = select(DiscordReplyCommand).where(DiscordReplyCommand.en)
    result = await session.execute(stmt)
    return list(result.scalars().all())
