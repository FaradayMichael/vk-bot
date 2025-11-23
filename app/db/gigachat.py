from gigachat.models import Messages
from sqlalchemy import select, delete

from app.models import GigachatMessage
from app.utils import db


async def create(session: db.Session, user_id: str, model: Messages) -> GigachatMessage:
    obj = GigachatMessage(
        attachments=model.attachments,
        name=model.name,
        user_id=user_id,
        id_=model.id_,
        data_for_context=model.data_for_context,
        role=model.role,
        content=model.content,
        function_call=model.function_call,
    )
    session.add(obj)
    await session.commit()
    return obj


async def get_by_user(
    session: db.Session,
    user_id: str,
) -> list[Messages]:
    stmt = select(GigachatMessage).where(user_id == GigachatMessage.user_id)
    result = await session.execute(stmt)
    return [Messages.parse_obj(i.__dict__) for i in result.scalars().all()]


async def delete_by_user(
    session: db.Session,
    user_id: str,
) -> None:
    stmt = delete(GigachatMessage).where(user_id == GigachatMessage.user_id)
    await session.execute(stmt)
    await session.commit()
