"""Quest models for daily/weekly tasks."""

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from telemon.database.models.base import Base, TimestampMixin


class UserQuest(Base, TimestampMixin):
    """A quest assigned to a user (daily or weekly)."""

    __tablename__ = "user_quests"

    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # User relationship
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.telegram_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Quest definition
    quest_type: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True
    )  # "daily" or "weekly"

    # Quest details
    task: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # e.g. "catch", "catch_type", "evolve", "trade", "battle_win", "pet"

    description: Mapped[str] = mapped_column(
        Text, nullable=False
    )  # Human-readable, e.g. "Catch 5 Water-type Pokemon"

    # Target and progress
    target_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    current_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Extra parameters (JSON for flexibility)
    # e.g. {"type": "water"}, {"species_id": 25}, {"gen": 3}
    params: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Reward
    reward_coins: Mapped[int] = mapped_column(Integer, nullable=False, default=100)

    # State
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    is_claimed: Mapped[bool] = mapped_column(Boolean, default=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Expiry
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)

    # Relationships
    user = relationship("User")

    def __repr__(self) -> str:
        return f"<UserQuest {self.id} {self.task} {self.current_count}/{self.target_count}>"

    @property
    def progress_text(self) -> str:
        """Get progress as text."""
        return f"{self.current_count}/{self.target_count}"

    @property
    def is_expired(self) -> bool:
        """Check if quest has expired."""
        return datetime.utcnow() > self.expires_at
