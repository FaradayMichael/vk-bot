from fastapi import APIRouter, Depends
from starlette.responses import JSONResponse

from db import (
    triggers as triggers_db
)
from misc.depends.db import (
    get as get_conn
)

from misc.db import (
    Connection
)

from models.triggers import (
    TriggersListResponse
)

router = APIRouter(
    prefix='/triggers',
    tags=['triggers']
)


@router.get('/', response_model=TriggersListResponse)
async def api_get_triggers(
        q: str = '',
        conn: Connection = Depends(get_conn)
) -> TriggersListResponse | JSONResponse:
    result = await triggers_db.get_list(conn, q)
    return TriggersListResponse(data=result)
