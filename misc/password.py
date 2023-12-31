from passlib import pwd
from passlib.hash import bcrypt


async def generate_password() -> str:
    return pwd.genword(entropy=56, length=12, charset='ascii_50')


async def get_password_hash(password: str, salt: str) -> str:
    return bcrypt.using(salt=salt).hash(password)
