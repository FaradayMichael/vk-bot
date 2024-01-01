from fastapi import Depends

from misc.depends.session import (
    get as get_session
)
from misc.handlers import (
    UnauthenticatedException,
    ForbiddenException
)
from misc.session import Session


async def check_auth(
        session: Session = Depends(get_session)
):
    if not session.user:
        raise UnauthenticatedException()
    if not session.user.is_authenticated:
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
