"""Pokedex entry model for tracking seen/caught Pokemon."""

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from telemon.database.models.base import Base


class PokedexEntry(Base):
    """Tracks which Pokemon a user has seen/caught."""

    __tablename__ = "pokedex_entries"

    # Composite primary key
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.telegram_id", ondelete="CASCADE"),
        primary_key=True,
    )
    species_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("pokemon_species.national_dex"),
        primary_key=True,
    )

    # Seen/caught status
    seen: Mapped[bool] = mapped_column(Boolean, default=False)
    caught: Mapped[bool] = mapped_column(Boolean, default=False)
    caught_shiny: Mapped[bool] = mapped_column(Boolean, default=False)

    # Count
    times_caught: Mapped[int] = mapped_column(Integer, default=0)

    # First catch timestamp
    first_caught_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Relationships
    user = relationship("User", back_populates="pokedex_entries")
    species = relationship("PokemonSpecies", lazy="joined")

    def __repr__(self) -> str:
        return f"<PokedexEntry user={self.user_id} species={self.species_id}>"
