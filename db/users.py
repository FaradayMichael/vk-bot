import logging
from typing import (
    Optional
)
from asyncpg import Record

from misc import db
from misc.db_tables import DBTables
from models.auth import RegisterModel

from models.users import (
    User,
    UserCreate
)

logger = logging.getLogger(__name__)

TABLE = DBTables.USERS


async def create_user(
        conn: db.Connection,
        user_data: RegisterModel,
        password: str
) -> Optional[User]:
    user_dict = user_data.model_dump()
    user_dict['password'] = password
    result = await db.create(
        conn,
        TABLE,
        user_dict
    )
    return db.record_to_model(User, result)


async def get_user(
        conn: db.Connection,
        pk: int
) -> Optional[User]:
    values = [pk]
    result = await db.get_by_where(
        conn,
        TABLE,
        'id = $1 AND en',
        values,
    )
    return await record_to_model_user(conn, result)


async def get_user_by_credentials(
        conn: db.Connection,
        email: str,
        password: str
) -> Optional[User]:
    result = await db.get_by_where(
        conn,
        TABLE,
        'email=$1 AND password=$2 AND en AND is_blocked=$3',
        values=[email, password, False]
    )
    return db.record_to_model(User, result)


async def email_exists(
        conn: db.Connection,
        email: str
) -> bool:
    user = await db.get_by_where(
        conn,
        TABLE,
        "email=$1 AND en=True",
        values=[email],
        fields=['id']
    )
    return True if user else False


async def login_exists(
        conn: db.Connection,
        login: str,
        id: Optional[int] = None
) -> bool:
    where = ["username=$1 AND en=True"]
    values = [login]
    if id:
        where.append('id <> $2')
        values.append(id)
    return await db.exists(
        conn=conn,
        table=TABLE,
        where=' AND '.join(where),
        values=values
    )


async def set_password(
        conn: db.Connection,
        email: str,
        password: str
) -> Optional[int]:
    data = await conn.fetchrow(
        f"UPDATE {TABLE} SET password=$2  WHERE email=$1 RETURNING id",
        email, password
    )
    return data['id'] if data else None


async def record_to_model_user(
        conn: db.Connection,
        record: Record
) -> Optional[User]:
    user = db.record_to_model(User, record)
    return user
