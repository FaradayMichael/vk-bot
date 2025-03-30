from fastapi import Depends

from utils.fastapi.depends.session import (
    get as get_session
)
from utils.fastapi.handlers import (
    UnauthenticatedException,
    ForbiddenException
)
from utils.fastapi.session import Session


async def check_auth(
        session: Session = Depends(get_session)
):
    if not session.user:
        raise UnauthenticatedException()


async def check_is_admin(
        session: Session = Depends(get_session)
):
    if not session.user:
        UnauthenticatedException()
    if session.is_admin:
        pass
    else:
        raise ForbiddenException()
