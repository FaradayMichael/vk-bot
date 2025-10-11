from fastapi import APIRouter, Depends
from starlette.responses import JSONResponse

from app.db import (
    triggers_answers as triggers_answers_db
)
from app.models.triggers_answers import (
    TriggerAnswer,
)
from app.schemas.triggers_answers import TriggerGroup
from app.utils.fastapi.depends.db import (
    get as get_db
)
from app.utils.db import (
    Session as DBSession
)

router = APIRouter(
    prefix='/triggers_answers',
    tags=['triggers_answers']
)


@router.get('/', response_model=None)
async def api_get_triggers_answers(
        trigger_q: str = '',
        answer_q: str = '',
        conn: DBSession = Depends(get_db)
) -> list[TriggerAnswer] | JSONResponse:
    return await triggers_answers_db.get_list(conn, trigger_q, answer_q)


@router.get('/triggers_group', response_model=list[TriggerGroup])
async def api_get_group_triggers(
        q: str = '',
        conn: DBSession = Depends(get_db)
) -> list[TriggerGroup] | JSONResponse:
    return await triggers_answers_db.get_triggers_group(conn, q)


@router.get('/find', response_model=None)
async def api_get_find_triggers(
        q: str = '',
        conn: DBSession = Depends(get_db)
) -> list[TriggerGroup] | JSONResponse:
    return await triggers_answers_db.get_for_like(conn, q)
