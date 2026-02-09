"""Market model for Pokemon marketplace."""

import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import BigInteger, Enum as SQLEnum, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from telemon.database.models.base import Base


class ListingStatus(str, Enum):
    """Listing status enum."""

    ACTIVE = "active"
    SOLD = "sold"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class MarketListing(Base):
    """Represents a Pokemon listing on the marketplace."""

    __tablename__ = "market_listings"

    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Seller
    seller_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.telegram_id"),
        nullable=False,
        index=True,
    )

    # Pokemon being sold
    pokemon_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pokemon.id"),
        nullable=False,
        unique=True,
    )

    # Price
    price: Mapped[int] = mapped_column(BigInteger, nullable=False)

    # Status
    status: Mapped[ListingStatus] = mapped_column(
        SQLEnum(ListingStatus),
        default=ListingStatus.ACTIVE,
        index=True,
    )

    # Timing
    listed_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    expires_at: Mapped[datetime] = mapped_column(nullable=False)
    sold_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Buyer (filled when sold)
    buyer_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("users.telegram_id"),
        nullable=True,
    )

    # Views tracking
    view_count: Mapped[int] = mapped_column(Integer, default=0)

    # Relationships
    seller = relationship("User", foreign_keys=[seller_id], back_populates="market_listings")
    buyer = relationship("User", foreign_keys=[buyer_id])
    pokemon = relationship("Pokemon", lazy="joined")

    def __repr__(self) -> str:
        return f"<MarketListing {self.id} pokemon={self.pokemon_id} price={self.price}>"

    @property
    def is_active(self) -> bool:
        """Check if listing is still active."""
        return self.status == ListingStatus.ACTIVE and datetime.utcnow() < self.expires_at

    @property
    def is_expired(self) -> bool:
        """Check if listing has expired."""
        return datetime.utcnow() >= self.expires_at and self.status == ListingStatus.ACTIVE
