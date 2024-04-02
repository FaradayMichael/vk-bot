from fastapi import (
    APIRouter,
    Depends,
    Request,
    Form
)
from fastapi.responses import (
    HTMLResponse,
    RedirectResponse
)
from jinja2 import Environment

from db import (
    triggers_history as triggers_history_db
)
from misc.db import Connection
from misc.depends.db import (
    get as get_conn
)
from misc.depends.session import (
    get as ges_session
)
from misc.depends.jinja import (
    get as get_jinja
)
from misc.session import Session
from models.base import BaseSearchQueryParams

router = APIRouter(prefix='/triggers_history')


@router.get('/', response_class=HTMLResponse)
async def triggers_history_view(
        request: Request,
        query_params: BaseSearchQueryParams = Depends(),
        jinja: Environment = Depends(get_jinja),
        session: Session = Depends(ges_session),
        conn: Connection = Depends(get_conn)
):
    rows = await triggers_history_db.get_list(conn, **query_params.model_dump())
    return jinja.get_template('service/triggers_history.html').render(
        user=session.user,
        request=request,
        rows=rows
    )


@router.post('/', response_class=RedirectResponse)
async def triggers_history_search_view(
        search: str | None = Form(default=None),
):
    return RedirectResponse(
        url=f'/service/triggers_history/{"?q=" + search if search else ""}',
        status_code=302
    )
