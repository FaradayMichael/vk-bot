from fastapi import APIRouter, Depends
from starlette.responses import JSONResponse

from db import (
    triggers_answers as triggers_answers_db
)
from misc.depends.db import (
    get as get_conn
)

from misc.db import (
    Connection
)

from models.triggers_answers import (
    TriggerAnswerListResponse,
    TriggerGroupListResponse
)

router = APIRouter(
    prefix='/triggers_answers',
    tags=['triggers_answers']
)


@router.get('/', response_model=TriggerAnswerListResponse)
async def api_get_triggers_answers(
        trigger_q: str = '',
        answer_q: str = '',
        conn: Connection = Depends(get_conn)
) -> TriggerAnswerListResponse | JSONResponse:
    result = await triggers_answers_db.get_list(conn, trigger_q, answer_q)
    return TriggerAnswerListResponse(data=result)


@router.get('/triggers_group', response_model=TriggerGroupListResponse)
async def api_get_group_triggers(
        q: str = '',
        conn: Connection = Depends(get_conn)
) -> TriggerGroupListResponse | JSONResponse:
    result = await triggers_answers_db.get_triggers_group(conn, q)
    return TriggerGroupListResponse(data=result)
