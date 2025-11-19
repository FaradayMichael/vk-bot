from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from jinja2 import Environment

from app.db import users as users_db
from app.utils.config import Config
from app.utils.fastapi.depends.db import get as get_db
from app.utils.fastapi.depends.conf import get as get_conf
from app.utils.fastapi.depends.session import get as ges_session
from app.utils.fastapi.depends.jinja import get as get_jinja
from app.utils.password import get_password_hash
from app.utils.fastapi.session import Session
from app.utils.db import Session as DBSession

router = APIRouter(prefix="/auth")


@router.get("/login", response_class=HTMLResponse)
async def login_view(
    jinja: Environment = Depends(get_jinja), session: Session = Depends(ges_session)
):
    return jinja.get_template("auth/login.html").render(user=session.user)


@router.post("/login", response_class=HTMLResponse)
async def login_submit(
    request: Request,
    username_or_email=Form(),
    password=Form(),
    jinja: Environment = Depends(get_jinja),
    session: Session = Depends(ges_session),
    conf: Config = Depends(get_conf),
    conn: DBSession = Depends(get_db),
):
    hashed_password = await get_password_hash(password, conf.salt)
    user = await users_db.get_by_credentials(conn, username_or_email, hashed_password)

    if not user:
        return jinja.get_template("auth/login.html").render(
            user=session.user, message="Wrong credentials", request=request
        )
    print(user)
    session.set_user(user)

    return RedirectResponse("/", status_code=302)


@router.get("/logout", response_class=HTMLResponse)
async def logout(
    session: Session = Depends(ges_session),
):
    session.reset_user()
    return RedirectResponse("/auth/login", status_code=302)
