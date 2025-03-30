from fastapi import (
    APIRouter,
    Depends,
    Request
)
from fastapi.responses import HTMLResponse
from jinja2 import Environment

from utils.fastapi.depends.session import (
    get as ges_session
)
from utils.fastapi.depends.jinja import (
    get as get_jinja
)
from utils.fastapi.session import Session

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
