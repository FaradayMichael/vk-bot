import logging
from typing import Annotated

from fastapi import (
    Request,
    Response,
    Security,
    Depends
)
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.security.api_key import (
    APIKeyQuery,
    APIKeyHeader,
    APIKeyCookie
)

from app.db import (
    users as users_db
)
from app.utils.config import Config
from app.utils.fastapi.depends.db import (
    get as get_db
)
from app.utils.fastapi.depends.redis import (
    get as get_redis
)
from app.utils.fastapi.depends.conf import (
    get as get_conf
)
from app.utils.fastapi.session import (
    COOKIE_SESSION_NAME,
    HEADERS_SESSION_NAME,
    TOKEN_SESSION_NAME,

    COOKIE_SESSION,
    HEADERS_SESSION,
    TOKEN_SESSION,

    Session,
    SessionType
)
from app.utils import redis, db
from app.utils.password import get_password_hash

logger = logging.getLogger(__name__)

api_key_query = APIKeyQuery(name=TOKEN_SESSION_NAME, auto_error=False)
api_key_header = APIKeyHeader(name=HEADERS_SESSION_NAME, auto_error=False)
api_key_cookie = APIKeyCookie(name=COOKIE_SESSION_NAME, auto_error=False)


async def get(
        request: Request,
        response: Response,

        basic_auth: Annotated[HTTPBasicCredentials, Depends(HTTPBasic(auto_error=False))],
        db_conn: db.Session = Depends(get_db),
        redis_conn: redis.Connection = Depends(get_redis),
        conf: Config = Depends(get_conf),
        api_key_query: str = Security(api_key_query),
        api_key_header: str = Security(api_key_header),
        api_key_cookie: str = Security(api_key_cookie),
) -> Session:
    session = await get_session(
        basic_auth,
        api_key_query,
        api_key_header,
        api_key_cookie,
        db_conn,
        redis_conn,
        conf
    )
    request.state.session = session
    if session.session_type == COOKIE_SESSION:
        response.set_cookie(
            COOKIE_SESSION_NAME,
            session.key,
            max_age=session.max_age
        )

    yield session

    await save_to_redis(
        session,
        redis_conn
    )


async def get_session(
        basic_auth: HTTPBasicCredentials,
        api_key_query: str,
        api_key_header: str,
        api_key_cookie: str,
        db_conn: db.Session,
        redis_conn: redis.Connection,
        conf: Config
) -> Session:
    values = [
        [api_key_cookie, COOKIE_SESSION],
        [api_key_header, HEADERS_SESSION],
        [api_key_query, TOKEN_SESSION]
    ]
    if basic_auth:
        hashed_password = await get_password_hash(basic_auth.password, conf.salt)
        user = await users_db.get_by_credentials(
            db_conn,
            basic_auth.username,
            hashed_password
        )
        if user:
            session = Session()
            session.set_user(user)
            return session

    for key, session_type in values:
        if key:
            session = await get_from_redis(session_type, key, redis_conn)
            if session is not None:
                session = await get_session_user(session, db_conn)
                return session

    return Session(
        session_type=COOKIE_SESSION
    )


async def get_from_redis(
        session_type: SessionType,
        key: str,
        redis_conn: redis.Connection
) -> Session | None:
    data = await redis.get(
        redis_conn,
        cache_key(key)
    )
    if data is None:
        return None
    session = Session(
        session_type=session_type,
        key=key,
        data=data
    )
    return session


async def save_to_redis(
        session: Session,
        redis_conn: redis.Connection
):
    await redis.setex(
        redis_conn,
        cache_key(session.key),
        session.max_age,
        session.data
    )


async def remove_from_redis(
        session: Session,
        redis_conn: redis.Connection
):
    await redis.del_(
        redis_conn,
        cache_key(session.key)
    )


async def get_session_user(
        session: Session,
        db_conn: db.Session
) -> Session:
    user = None
    if session.session_user_id:
        user = await users_db.get(db_conn, session.session_user_id)
    session.set_user(
        user=user
    )
    return session


def cache_key(key: str) -> str:
    return f'session_{key}'
