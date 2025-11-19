from sqlalchemy.orm import Mapped, mapped_column

from .base import BaseTable


class User(BaseTable):
    __tablename__ = "users"

    username: Mapped[str] = mapped_column(index=True)
    email: Mapped[str] = mapped_column(index=True, unique=True)
    password: Mapped[str]
    is_admin: Mapped[bool] = mapped_column(default=False)
