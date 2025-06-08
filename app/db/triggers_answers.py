from sqlalchemy import select, func, and_, bindparam

from app.models.triggers_answers import TriggerAnswer
from app.schemas.triggers_answers import TriggerAnswerCreate, TriggerGroup

from app.utils import db


async def create(
        session: db.Session,
        model: TriggerAnswerCreate
) -> TriggerAnswer:
    obj = TriggerAnswer(
        **model.model_dump()
    )
    session.add(obj)
    await session.commit()
    return obj


async def delete(
        session: db.Session,
        obj: TriggerAnswer
) -> None:
    await session.delete(obj)
    await session.commit()


async def get(
        session: db.Session,
        pk: int
) -> TriggerAnswer | None:
    return await session.get(TriggerAnswer, pk)


async def get_list(
        session: db.Session,
        trigger_q: str = '',
        answer_q: str = '',
) -> list[TriggerAnswer]:
    stmt = select(TriggerAnswer).where(
        TriggerAnswer.trigger.icontains(f"{trigger_q.strip().lower()}"),
        TriggerAnswer.answer.icontains(f"{answer_q.strip().lower()}"),
    )
    # print(stmt)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_triggers_group(
        session: db.Session,
        q: str = ''
) -> list[TriggerGroup]:
    stmt = select(
        TriggerAnswer.trigger,
        func.json_agg(
            func.json_build_object(
                "id", TriggerAnswer.id,
                "answer", TriggerAnswer.answer,
                "attachment", TriggerAnswer.attachment
            )
        ).label("answers")
    ).where(
        and_(
            TriggerAnswer.en,
            TriggerAnswer.trigger.icontains(f"{q.strip().lower()}"),
        )
    ).group_by(TriggerAnswer.trigger)
    result = await session.execute(stmt)
    return [
        TriggerGroup.model_validate(i) for i in result.mappings().all()
    ]


async def get_for_like(
        session: db.Session,
        q: str = ''
) -> list[TriggerGroup]:
    stmt = select(
        TriggerAnswer.trigger,
        func.json_agg(
            func.json_build_object(
                "id", TriggerAnswer.id,
                "answer", TriggerAnswer.answer,
                "attachment", TriggerAnswer.attachment
            )
        ).label("answers")
    ).where(
        and_(
            TriggerAnswer.en,
            bindparam('q', q.strip().lower()).icontains(TriggerAnswer.trigger),
            # TriggerAnswer.trigger.icontains(f"{q.strip().lower()}"),
        )
    ).group_by(TriggerAnswer.trigger)
    result = await session.execute(stmt)
    return [
        TriggerGroup.model_validate(i) for i in result.mappings().all()
    ]
