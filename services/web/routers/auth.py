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
    users as users_db
)
from misc.config import Config
from misc.db import Connection
from misc.depends.db import (
    get as get_conn
)
from misc.depends.conf import (
    get as get_conf
)
from misc.depends.session import (
    get as ges_session
)
from misc.depends.jinja import (
    get as get_jinja
)
from misc.password import get_password_hash
from misc.session import Session

router = APIRouter(prefix='/auth')


@router.get('/login', response_class=HTMLResponse)
async def login_view(
        request: Request,
        jinja: Environment = Depends(get_jinja),
        session: Session = Depends(ges_session)
):
    return jinja.get_template('auth/login.html').render(
        user=session.user
    )


@router.post('/login', response_class=HTMLResponse)
async def login_submit(
        request: Request,
        username_or_email=Form(),
        password=Form(),
        jinja: Environment = Depends(get_jinja),
        session: Session = Depends(ges_session),
        conf: Config = Depends(get_conf),
        conn: Connection = Depends(get_conn)
):
    hashed_password = await get_password_hash(password, conf.salt)
    user = await users_db.get_user_by_credentials(
        conn,
        username_or_email,
        hashed_password
    )

    if not user:
        return jinja.get_template('auth/login.html').render(
            user=session.user,
            message="Wrong credentials",
            request=request
        )

    session.set_user(user)

    return RedirectResponse('/', status_code=302)


@router.get('/logout', response_class=HTMLResponse)
async def logout(
        session: Session = Depends(ges_session),
):
    session.reset_user()
    return RedirectResponse('/auth/login', status_code=302)
