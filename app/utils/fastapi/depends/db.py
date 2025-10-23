import logging

import fastapi

from app.utils import db
from app.utils.fastapi.state import State

logger = logging.getLogger(__name__)


async def get(request: fastapi.Request) -> db.Session:
    state: State = request.app.state
    try:
        sm = state.db_helper.session_maker
    except AttributeError:
        raise RuntimeError('Application state has no db pool')
    else:
        async with sm(expire_on_commit=False) as session:
            yield session
