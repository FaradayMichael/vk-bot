from sqlalchemy.orm import Mapped, mapped_column

from .base import BaseTable


class TriggerAnswer(BaseTable):
    __tablename__ = "triggers_answers"

    trigger: Mapped[str] = mapped_column(index=True, unique=True)
    answer: Mapped[str | None] = mapped_column(default=None)
    attachment: Mapped[str | None] = mapped_column(default=None)
