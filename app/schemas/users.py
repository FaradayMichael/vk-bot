from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.base import (
    SuccessResponse,
    ListData,
)


class UserCreate(BaseModel):
    username: str
    email: str


class BaseUser(BaseModel):
    id: int = 0
    en: bool | None = None

    username: str
    email: str
    is_admin: bool = False

    ctime: datetime | None = Field(None)
    atime: datetime | None = None
    dtime: datetime | None = None

    @property
    def is_authenticated(self):
        return bool(self.id)


BaseUser.model_rebuild()


class Anonymous(BaseUser):
    username: str = ""
    email: str = ""


class User(BaseUser):
    pass


class UsersSuccessResponse(SuccessResponse):
    data: User


class UsersListData(ListData):
    items: list[User] = []


class UsersListSuccessResponse(SuccessResponse):
    data: UsersListData
