from fastapi import APIRouter, Depends
from starlette.responses import JSONResponse
from jinja2 import Environment as JinjaEnvironment

from business_logic.mailing import send_password_email
from db import (
    users as users_db
)
from misc.depends.db import (
    get as get_conn
)
from misc.depends.conf import (
    get as get_conf
)
from misc.depends.session import (
    get as get_session
)
from misc.depends.smtp import (
    get as get_smtp
)
from misc.depends.jinja import (
    get as get_jinja
)
from misc.depends.redis import (
    get as get_redis
)
from misc.config import Config
from misc.db import (
    Connection
)
from misc.session import Session
from misc.smtp import (
    SMTP as SMTPConnection
)
from misc.redis import (
    Connection as RedisConnection
)
from misc.handlers import error_400
from misc.password import generate_password, get_password_hash
from models.auth import (
    RegisterModel,
    MeSuccessResponse,
    MeResponse
)

router = APIRouter(
    prefix='/users'
)


@router.post('/', response_model=MeSuccessResponse)
async def api_create_user(
        data: RegisterModel,
        conn: Connection = Depends(get_conn),
        session: Session = Depends(get_session),
        config: Config = Depends(get_conf),
        smtp: SMTPConnection = Depends(get_smtp),
        jinja: JinjaEnvironment = Depends(get_jinja),
) -> MeSuccessResponse | JSONResponse:
    if await users_db.email_exists(conn, data.email):
        return await error_400("Email already exist")
    if await users_db.login_exists(conn, data.username):
        return await error_400("Username already exist")

    password = await generate_password()
    hashed_password = await get_password_hash(password, config.salt)
    user = await users_db.create_user(
        conn,
        data,
        hashed_password
    )
    if not user:
        return await error_400()
    await send_password_email(smtp, user.email, password, jinja, config)
    session.set_user(user)
    return MeSuccessResponse(data=MeResponse(me=user, token=session.key))
