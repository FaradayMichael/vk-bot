from fastapi import Depends

from misc.depends.session import (
    get as get_session
)
from misc.handlers import (
    ForbiddenException,
    UnauthenticatedExceptionWeb
)
from misc.session import Session


async def check_auth(
        session: Session = Depends(get_session)
):
    if not session.user:
        raise UnauthenticatedExceptionWeb()
    if not session.user.is_authenticated:
        raise UnauthenticatedExceptionWeb()


async def check_is_admin(
        session: Session = Depends(get_session)
):
    if not session.user:
        UnauthenticatedExceptionWeb()
    if session.is_admin:
        pass
    else:
        raise ForbiddenException()
