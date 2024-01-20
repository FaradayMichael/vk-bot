from fastapi import APIRouter, Depends, Request
from jinja2 import Environment
from starlette.responses import HTMLResponse

from misc.depends.session import (
    get as ges_session
)
from misc.depends.jinja import (
    get as get_jinja
)
from misc.session import Session

router = APIRouter()


@router.get('/', response_class=HTMLResponse)
async def index(
        request: Request,
        jinja: Environment = Depends(get_jinja),
        session: Session = Depends(ges_session)
):
    return jinja.get_template("index.html").render(
        user=session.user,
        request=request
    )
