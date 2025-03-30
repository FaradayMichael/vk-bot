from pydantic import (
    BaseModel,
    constr
)

from utils.consts import (
    EMAIL_REGEX,
    LOGIN
)
from models_old.base import SuccessResponse
from schemas.users import BaseUser


class MeResponse(BaseModel):
    token: str
    me: BaseUser


class MeSuccessResponse(SuccessResponse):
    data: MeResponse


class PasswordModel(BaseModel):
    password: constr(strip_whitespace=True)


class RegisterModel(BaseModel):
    email: constr(to_lower=True, strip_whitespace=True, pattern=EMAIL_REGEX)
    username: constr(strip_whitespace=True, pattern=LOGIN)


class LoginModel(BaseModel):
    username_or_email: constr(to_lower=True, strip_whitespace=True)
    password: constr(strip_whitespace=True)
