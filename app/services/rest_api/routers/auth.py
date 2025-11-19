import logging

from fastapi import APIRouter, Depends
from starlette.responses import JSONResponse

from app.db import users as users_db
from app.schemas.auth import MeSuccessResponse, MeResponse, LoginModel, PasswordModel
from app.schemas.base import SuccessResponse
from app.schemas.users import Anonymous, User
from app.services.rest_api.depends.auth import check_auth
from app.utils.config import Config
from app.utils.db import (
    Session as DBSession,
)
from app.utils.fastapi.depends.conf import get as get_conf
from app.utils.fastapi.depends.db import get as get_db
from app.utils.fastapi.depends.session import get as get_session
from app.utils.fastapi.handlers import error_404
from app.utils.password import get_password_hash
from app.utils.fastapi.session import Session

router = APIRouter(prefix="/auth", tags=["auth"])

logger = logging.getLogger(__name__)


@router.get("/me", name="me", response_model=MeSuccessResponse)
async def about_me(session: Session = Depends(get_session)):
    print(session.user)
    match session.user:
        case None:
            return MeSuccessResponse(data=MeResponse(me=Anonymous(), token=session.key))
        case _:
            return MeSuccessResponse(
                data=MeResponse(me=User(**session.user.__dict__), token=session.key)
            )


@router.post("/login", name="login", response_model=MeSuccessResponse)
async def login_user(
    auth: LoginModel,
    conn: DBSession = Depends(get_db),
    session: Session = Depends(get_session),
    conf: Config = Depends(get_conf),
) -> MeSuccessResponse | JSONResponse:
    hashed_password = await get_password_hash(auth.password, conf.salt)
    user = await users_db.get_by_credentials(
        conn, auth.username_or_email, hashed_password
    )

    if not user:
        return await error_404()

    session.set_user(user)
    return MeSuccessResponse(
        data=MeResponse(me=User(**session.user.__dict__), token=session.key)
    )


@router.post("/logout", name="logout", response_model=MeSuccessResponse)
async def logout(
    session: Session = Depends(get_session),
) -> MeSuccessResponse | JSONResponse:
    session.reset_user()

    return MeSuccessResponse(
        data=MeResponse(me=session.user or Anonymous(), token=session.key)
    )


@router.post(
    "/set_password", response_model=SuccessResponse, dependencies=[Depends(check_auth)]
)
async def set_new_password(
    data: PasswordModel,
    conn: DBSession = Depends(get_db),
    session: Session = Depends(get_session),
    conf: Config = Depends(get_conf),
) -> SuccessResponse | JSONResponse:
    hashed_password = await get_password_hash(data.password, conf.salt)
    await users_db.set_password(conn, session.user, hashed_password)
    return SuccessResponse()
