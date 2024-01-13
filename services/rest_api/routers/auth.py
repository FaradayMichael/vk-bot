import logging

from fastapi import (
    APIRouter,
    Depends
)
from starlette.responses import JSONResponse

from db import (
    users as users_db
)
from misc.config import Config
from misc.db import Connection
from misc.depends.conf import (
    get as get_conf
)
from misc.depends.db import (
    get as get_db
)
from misc.depends.session import (
    get as get_session
)
from misc.handlers import error_404
from misc.password import get_password_hash
from misc.session import Session
from models.auth import (
    MeSuccessResponse,
    MeResponse,
    LoginModel
)
from models.users import Anonymous

router = APIRouter(
    prefix='/auth',
    tags=['auth']
)

logger = logging.getLogger(__name__)


@router.get('/me', name='me', response_model=MeSuccessResponse)
async def about_me(
        session: Session = Depends(get_session)
):
    match session.user:
        case None:
            return MeSuccessResponse(data=MeResponse(me=Anonymous(), token=session.key))
        case _:
            return MeSuccessResponse(data=MeResponse(me=session.user, token=session.key))


@router.post('/login', name='login', response_model=MeSuccessResponse)
async def login_user(
        auth: LoginModel,
        conn: Connection = Depends(get_db),
        session: Session = Depends(get_session),
        conf: Config = Depends(get_conf)
) -> MeSuccessResponse | JSONResponse:
    hashed_password = await get_password_hash(auth.password, conf.salt)
    user = await users_db.get_user_by_credentials(
        conn,
        auth.username_or_email,
        hashed_password
    )

    if not user:
        return await error_404()

    session.set_user(user)
    return MeSuccessResponse(
        data=MeResponse(
            me=session.user,
            token=session.key
        )
    )


@router.post('/logout', name='logout', response_model=MeSuccessResponse)
async def logout(
        session: Session = Depends(get_session)
) -> MeSuccessResponse | JSONResponse:
    session.reset_user()

    return MeSuccessResponse(data=MeResponse(me=session.user, token=session.key))
