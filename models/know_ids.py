from sqlalchemy import Text, JSON
from sqlalchemy.orm import Mapped, mapped_column

from .base import BaseTable


class KnowId(BaseTable):
    __tablename__ = 'know_ids'

    name: Mapped[str]
    note: Mapped[str | None] = mapped_column(Text, default=None)
    extra_data: Mapped[dict | None] = mapped_column(JSON, default=None)
    vk_id: Mapped[int | None] = mapped_column(default=None)
    discord_id: Mapped[int | None] = mapped_column(default=None)
