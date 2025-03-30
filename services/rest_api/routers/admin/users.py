from fastapi import APIRouter, Depends
from starlette.responses import JSONResponse
from jinja2 import Environment as JinjaEnvironment

from business_logic.mailing import send_password_email
from db import (
    users as users_db
)
from schemas.auth import (
    RegisterModel
)
from schemas.users import User
from utils.fastapi.depends.db import (
    get as get_db
)
from utils.fastapi.depends.conf import (
    get as get_conf
)
from utils.fastapi.depends.smtp import (
    get as get_smtp
)
from utils.fastapi.depends.jinja import (
    get as get_jinja
)
from utils.fastapi.handlers import error_400
from utils.db import (
    Session as DBSession,
)
from utils.config import Config

from utils.smtp import (
    SMTP as SMTPConnection
)
from utils.password import (
    generate_password,
    get_password_hash
)

router = APIRouter(
    prefix='/users'
)


@router.post('/', response_model=User)
async def api_create_user(
        data: RegisterModel,
        conn: DBSession = Depends(get_db),
        config: Config = Depends(get_conf),
        smtp: SMTPConnection = Depends(get_smtp),
        jinja: JinjaEnvironment = Depends(get_jinja),
) -> User | JSONResponse:
    if await users_db.email_exists(conn, data.email):
        return await error_400("Email already exist")
    if await users_db.login_exists(conn, data.username):
        return await error_400("Username already exist")

    password = await generate_password()
    hashed_password = await get_password_hash(password, config.salt)
    user = await users_db.create(
        conn,
        data,
        hashed_password
    )
    if not user:
        return await error_400()
    await send_password_email(smtp, user.email, password, jinja, config)
    return user
