"""Achievement/badge models."""

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from telemon.database.models.base import Base


class UserAchievement(Base):
    """Tracks which achievements a user has unlocked."""

    __tablename__ = "user_achievements"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.telegram_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Achievement key (e.g. "first_catch", "catch_100")
    achievement_id: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )

    unlocked_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    # Relationships
    user = relationship("User")

    def __repr__(self) -> str:
        return f"<UserAchievement {self.achievement_id} user={self.user_id}>"
