import secrets
import typing

from models.users import (
    BaseUser,
    Anonymous
)

COOKIE_SESSION = 'cookie'
HEADERS_SESSION = 'headers'
TOKEN_SESSION = 'token'

COOKIE_SESSION_NAME = 'sid'
HEADERS_SESSION_NAME = 'X-SID'
TOKEN_SESSION_NAME = 'sid'

ANONYMOUS_EXPIRES = 3600
AUTHENTICATED_EXPIRES = 2592000

SessionType = typing.Literal[
    COOKIE_SESSION,
    HEADERS_SESSION,
    TOKEN_SESSION
]


class Session(object):
    def __init__(
            self,
            session_type: typing.Optional[SessionType] = None,
            key: typing.Optional[str] = None,
            data: typing.Optional[dict] = None
    ):
        super().__init__()
        self.reset_user()
        if data:
            self._data = data
        self._key: str = key or new_key()
        self._session_type: SessionType = session_type or COOKIE_SESSION
        self._user = Anonymous()

    @property
    def user(self) -> BaseUser:
        return self._user

    def set_user(self, user: BaseUser):
        self._user = user
        if user:
            self._data['user_id'] = user.id
            self._data['is_admin'] = user.is_admin

    def reset_user(self):
        self._user: BaseUser = Anonymous()
        self._data: dict = {'user_id': None, 'is_admin': None}

    @property
    def key(self):
        return self._key

    @property
    def session_type(self):
        return self._session_type

    @property
    def max_age(self):
        if self.user and self.user.is_authenticated:
            return AUTHENTICATED_EXPIRES
        return ANONYMOUS_EXPIRES

    @property
    def data(self):
        return self._data

    @property
    def session_user_id(self):
        if self._data:
            return self._data.get('user_id')
        return None

    @property
    def is_admin(self) -> bool:
        if self._data:
            return self._data.get("is_admin")
        return False

    @key.setter
    def key(self, value):
        self._key = value


def new_key():
    return secrets.token_hex(24)
