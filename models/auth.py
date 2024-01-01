from pydantic import (
    BaseModel,
    constr
)

from misc.consts import (
    EMAIL_REGEX,
    LOGIN
)
from .base import SuccessResponse
from .users import BaseUser


class MeResponse(BaseModel):
    token: str
    me: BaseUser


class MeSuccessResponse(SuccessResponse):
    data: MeResponse


class RegisterModel(BaseModel):
    email: constr(to_lower=True, strip_whitespace=True, pattern=EMAIL_REGEX)
    username: constr(strip_whitespace=True, pattern=LOGIN)


class LoginModel(BaseModel):
    username: constr(to_lower=True, strip_whitespace=True, pattern=EMAIL_REGEX)
    password: constr(strip_whitespace=True)
