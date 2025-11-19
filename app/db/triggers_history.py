from sqlalchemy import select, or_, cast, String, and_

from app.models.triggers_history import TriggerHistory, TriggerAnswer
from app.schemas.triggers_history import TriggersHistoryNew

from app.utils import db


async def create(session: db.Session, model: TriggersHistoryNew) -> TriggerHistory:
    obj = TriggerHistory(**model.model_dump())
    session.add(obj)
    await session.commit()
    return obj


async def get_list(
    session: db.Session, q_words: list[str] | None = None
) -> list[TriggerHistory]:
    if q_words is None:
        q_words = []

    search_fields = {
        cast(TriggerHistory.vk_id, String),
        TriggerAnswer.trigger,
        TriggerAnswer.answer,
        # KnowId.name
    }

    stmt = (
        select(TriggerHistory)
        .join(TriggerAnswer)
        .where(
            and_(
                *[or_(*[s_f.ilike(f"%{q}%") for s_f in search_fields]) for q in q_words]
            )
        )
    )

    result = await session.execute(stmt)
    return list(result.scalars().all())
