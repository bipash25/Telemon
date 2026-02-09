"""Battle model for PvP battles."""

import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import BigInteger, Enum as SQLEnum, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from telemon.database.models.base import Base


class BattleStatus(str, Enum):
    """Battle status enum."""

    PENDING = "pending"  # Challenge sent
    ACTIVE = "active"  # Battle in progress
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FORFEITED = "forfeited"


class Battle(Base):
    """Represents a PvP battle."""

    __tablename__ = "battles"

    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Participants
    player1_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.telegram_id"),
        nullable=False,
        index=True,
    )
    player2_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.telegram_id"),
        nullable=False,
        index=True,
    )

    # Winner (null if ongoing or draw)
    winner_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("users.telegram_id"),
        nullable=True,
    )

    # Teams (list of Pokemon UUIDs)
    player1_team: Mapped[list] = mapped_column(ARRAY(UUID(as_uuid=True)), default=list)
    player2_team: Mapped[list] = mapped_column(ARRAY(UUID(as_uuid=True)), default=list)

    # Current active Pokemon index
    player1_active_index: Mapped[int] = mapped_column(Integer, default=0)
    player2_active_index: Mapped[int] = mapped_column(Integer, default=0)

    # Battle state (JSON for complex state)
    battle_state: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Turn tracking
    current_turn: Mapped[int] = mapped_column(Integer, default=1)
    whose_turn: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    # Status
    status: Mapped[BattleStatus] = mapped_column(
        SQLEnum(BattleStatus),
        default=BattleStatus.PENDING,
        index=True,
    )

    # Message tracking for UI
    chat_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    message_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    # Battle log
    battle_log: Mapped[list] = mapped_column(JSONB, default=list)

    # Timing
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    started_at: Mapped[datetime | None] = mapped_column(nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(nullable=True)
    last_action_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Rewards
    winner_coins: Mapped[int] = mapped_column(Integer, default=0)
    winner_xp: Mapped[int] = mapped_column(Integer, default=0)

    # Ranked battle
    is_ranked: Mapped[bool] = mapped_column(default=True)
    rating_change_p1: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rating_change_p2: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Relationships
    player1 = relationship("User", foreign_keys=[player1_id])
    player2 = relationship("User", foreign_keys=[player2_id])
    winner = relationship("User", foreign_keys=[winner_id])

    def __repr__(self) -> str:
        return f"<Battle {self.id} {self.player1_id} vs {self.player2_id}>"

    @property
    def is_active(self) -> bool:
        """Check if battle is currently active."""
        return self.status == BattleStatus.ACTIVE

    @property
    def is_pending(self) -> bool:
        """Check if battle is pending acceptance."""
        return self.status == BattleStatus.PENDING

    @property
    def is_completed(self) -> bool:
        """Check if battle has ended."""
        return self.status in (
            BattleStatus.COMPLETED,
            BattleStatus.FORFEITED,
            BattleStatus.CANCELLED,
        )
