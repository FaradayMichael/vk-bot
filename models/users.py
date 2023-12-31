from enum import Enum
from datetime import (
    datetime
)
from typing import (
    Optional,
    List
)

from decimal import Decimal
from pydantic import (
    BaseModel,
    Field,
    constr
)
from misc.consts import (
    EMAIL_REGEX,
    LOGIN
)
from models.base import (
    SuccessResponse,
    ListData,
)


class UserCreate(BaseModel):
    username: str
    email: str


class BaseUser(BaseModel):
    id: int = 0
    en: Optional[bool] = None

    username: str
    email: str
    is_admin: bool = False

    ctime: Optional[datetime] = Field(None)
    atime: Optional[datetime] = None
    dtime: Optional[datetime] = None

    @property
    def is_authenticated(self):
        return bool(self.id)


BaseUser.model_rebuild()


class Anonymous(BaseUser):
    username: str = ''
    email: str = ''


class User(BaseUser):
    pass


class UsersSuccessResponse(SuccessResponse):
    data: User


class UsersListData(ListData):
    items: List[User] = []


class UsersListSuccessResponse(SuccessResponse):
    data: UsersListData
