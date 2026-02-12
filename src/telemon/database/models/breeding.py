"""Breeding models — Daycare and Eggs."""

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from telemon.database.models.base import Base, TimestampMixin


class DaycareSlot(Base, TimestampMixin):
    """A daycare slot holding one Pokemon for breeding."""

    __tablename__ = "daycare_slots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Owner
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.telegram_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Pokemon in slot
    pokemon_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pokemon.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Slot number (1 or 2)
    slot: Mapped[int] = mapped_column(Integer, nullable=False)

    # Relationships
    pokemon = relationship("Pokemon", lazy="joined")


class PokemonEgg(Base, TimestampMixin):
    """An egg waiting to hatch."""

    __tablename__ = "pokemon_eggs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Owner
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.telegram_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Species that will hatch
    species_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("pokemon_species.national_dex"),
        nullable=False,
    )

    # Parent references (for display only, nullable if parents released)
    parent1_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    parent2_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )

    # Pre-determined IVs (set at egg creation via inheritance)
    iv_hp: Mapped[int] = mapped_column(Integer, default=0)
    iv_attack: Mapped[int] = mapped_column(Integer, default=0)
    iv_defense: Mapped[int] = mapped_column(Integer, default=0)
    iv_sp_attack: Mapped[int] = mapped_column(Integer, default=0)
    iv_sp_defense: Mapped[int] = mapped_column(Integer, default=0)
    iv_speed: Mapped[int] = mapped_column(Integer, default=0)

    # Hatching progress
    steps_remaining: Mapped[int] = mapped_column(Integer, default=5120)
    steps_total: Mapped[int] = mapped_column(Integer, default=5120)

    # Shiny (determined at egg creation)
    is_shiny: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    species = relationship("PokemonSpecies", lazy="joined")
