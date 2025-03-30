from urllib.parse import (
    quote_plus
)

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
from schemas.base import (
    BaseSearchQueryParams
)
from utils.fastapi.depends.db import (
    get as get_db
)
from utils.fastapi.depends.session import (
    get as ges_session
)
from utils.fastapi.depends.jinja import (
    get as get_jinja
)
from utils.fastapi.session import Session
from utils.db import (
    Session as DBSession
)

router = APIRouter(prefix='/triggers_history')


@router.get('/', response_class=HTMLResponse)
async def triggers_history_view(
        request: Request,
        query_params: BaseSearchQueryParams = Depends(),
        jinja: Environment = Depends(get_jinja),
        session: Session = Depends(ges_session),
        conn: DBSession = Depends(get_db)
):
    q = query_params.q.split('|')
    q = [s.strip() for s in q]
    rows = await triggers_history_db.get_list(conn, q)
    return jinja.get_template('service/triggers_history.html').render(
        user=session.user,
        request=request,
        rows=rows,
        q=query_params.q,
    )


@router.post('/', response_class=RedirectResponse)
async def triggers_history_search_view(
        search: str | None = Form(default=None),
):
    return RedirectResponse(
        url=f'/service/triggers_history/{"?q=" + quote_plus(search) if search else ""}',
        status_code=302
    )
