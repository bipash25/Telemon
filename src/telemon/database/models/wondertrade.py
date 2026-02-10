"""Wonder Trade model — anonymous Pokemon exchange pool."""

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from telemon.database.models.base import Base, TimestampMixin


class WonderTrade(Base, TimestampMixin):
    """A Pokemon deposited into the Wonder Trade pool."""

    __tablename__ = "wonder_trades"

    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Depositor
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.telegram_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Pokemon being traded
    pokemon_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pokemon.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Species info (cached for display without joins)
    species_id: Mapped[int] = mapped_column(Integer, nullable=False)
    species_name: Mapped[str] = mapped_column(String(50), nullable=False)
    level: Mapped[int] = mapped_column(Integer, nullable=False)
    is_shiny: Mapped[bool] = mapped_column(Boolean, default=False)

    # State
    is_matched: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    matched_with_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )  # The other WonderTrade entry
    matched_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationships
    user = relationship("User")
    pokemon = relationship("Pokemon")

    def __repr__(self) -> str:
        return f"<WonderTrade {self.id} user={self.user_id} pokemon={self.species_name}>"
