from passlib import pwd
import bcrypt


async def generate_password() -> str:
    return pwd.genword(entropy=56, length=12, charset="ascii_50")


async def get_password_hash(password: str, salt: str) -> str:
    return (bcrypt.hashpw(password.encode("utf-8"), salt.encode())).decode("utf-8")
