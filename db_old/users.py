import logging
from typing import (
    Optional
)

from misc import db
from utils.db_tables import DBTables
from schemas.auth import RegisterModel

from schemas.users import (
    User
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
    return db.record_to_model(User, result)


async def get_user_by_credentials(
        conn: db.Connection,
        username_or_email: str,
        password: str
) -> Optional[User]:
    result = await db.get_by_where(
        conn,
        TABLE,
        '(email=$1 OR username=$1) AND password=$2 AND en',
        values=[username_or_email, password]
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
        pk: Optional[int] = None
) -> bool:
    where = ["username=$1 AND en=True"]
    values = [login]
    if pk:
        where.append('id <> $2')
        values.append(pk)
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
