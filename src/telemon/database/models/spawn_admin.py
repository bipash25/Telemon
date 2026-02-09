"""Spawn admin model for users allowed to use /spawn command."""

from sqlalchemy import BigInteger, Text
from sqlalchemy.orm import Mapped, mapped_column

from telemon.database.models.base import Base, TimestampMixin


class SpawnAdmin(Base, TimestampMixin):
    """Users who are allowed to use /spawn command in any group."""

    __tablename__ = "spawn_admins"

    # User's Telegram ID
    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    # Who added this user (bot owner or another admin)
    added_by: Mapped[int] = mapped_column(BigInteger, nullable=False)

    # Optional notes
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<SpawnAdmin user_id={self.user_id}>"
