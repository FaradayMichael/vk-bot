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
from jinja2 import (
    Environment
)

from db import (
    triggers_answers as triggers_answers_db
)
from schemas.triggers_answers import (
    TriggerAnswerCreate
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
from utils.fastapi.session import (
    Session
)
from utils.db import (
    Session as DBSession
)

router = APIRouter(prefix='/triggers_answers')


@router.get('/', response_class=HTMLResponse)
async def triggers_answers_view(
        request: Request,
        jinja: Environment = Depends(get_jinja),
        session: Session = Depends(ges_session),
        conn: DBSession = Depends(get_db)
):
    rows = await triggers_answers_db.get_list(conn)
    return jinja.get_template('service/triggers_answers.html').render(
        user=session.user,
        request=request,
        rows=rows
    )


@router.post('/', response_class=RedirectResponse)
async def triggers_answers_create(
        trigger: str = Form(),
        answer: str = Form(),
        attachment: str = Form(default=None),
        conn: DBSession = Depends(get_db)
):
    attachment = attachment or ''
    if trigger.strip() and answer.strip() + attachment.strip():
        await triggers_answers_db.create(
            conn,
            TriggerAnswerCreate(
                trigger=trigger,
                answer=answer,
                attachment=attachment
            )
        )
    return RedirectResponse('/service/triggers_answers', status_code=302)


@router.post('/delete', response_class=RedirectResponse)
async def triggers_answers_delete(
        pk: int = Form(),
        conn: DBSession = Depends(get_db)
):
    exist = await triggers_answers_db.get(conn, pk)
    if exist:
        await triggers_answers_db.delete(conn, exist)
    return RedirectResponse('/service/triggers_answers', status_code=302)
