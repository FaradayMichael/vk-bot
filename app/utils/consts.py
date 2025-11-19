from enum import StrEnum

DAY = 86400  # in seconds

RECOVER = "recover"
REGISTER = "register"
UPDATE_LOGIN = "upd_login"

EMAIL_REGEX = r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"
PHONE_REGEX = r"\+?[0-9\- ]{1,}\(?[0-9]{3,}\)?[0-9\- ]{4,}"
LOGIN = r"[A-Za-z][A-Za-z\d.-]{0,19}$"
EMAIL_OR_PHONE_REGEX = rf"(?P<phone>{PHONE_REGEX})|(?P<email>{EMAIL_REGEX})"
NAME_REGEX = r"[A-ZА-Я]\w+"
TELEGRAM_NAME = r"^@?[a-zA-Z][a-zA-Z0-9]{4,31}$"

LIMIT_PER_PAGE = 100


class LangsEnum(StrEnum):
    EN = "en"
    RU = "ru"
    ES = "es"
    CN = "cn"


VK_SERVICE_REDIS_QUEUE = "vk_service_redis_queue"
