"""Move model - static data for all moves."""

from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from telemon.database.models.base import Base


class Move(Base):
    """Static data for a Pokemon move."""

    __tablename__ = "moves"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Basic info
    name: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    name_lower: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    # Type and category
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    category: Mapped[str] = mapped_column(String(20), nullable=False)  # physical, special, status

    # Power and accuracy
    power: Mapped[int | None] = mapped_column(Integer, nullable=True)
    accuracy: Mapped[int | None] = mapped_column(Integer, nullable=True)  # None = always hits
    pp: Mapped[int] = mapped_column(Integer, default=20)

    # Priority (-7 to +5, 0 is normal)
    priority: Mapped[int] = mapped_column(Integer, default=0)

    # Effect
    effect: Mapped[str | None] = mapped_column(Text, nullable=True)
    effect_chance: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Target type
    target: Mapped[str] = mapped_column(String(30), default="selected-pokemon")

    # Damage class details
    crit_rate: Mapped[int] = mapped_column(Integer, default=0)  # 0 = normal, 1 = high, 2 = always

    # Move flags
    makes_contact: Mapped[bool] = mapped_column(Boolean, default=False)
    is_sound_based: Mapped[bool] = mapped_column(Boolean, default=False)
    is_punch: Mapped[bool] = mapped_column(Boolean, default=False)
    is_bite: Mapped[bool] = mapped_column(Boolean, default=False)
    is_pulse: Mapped[bool] = mapped_column(Boolean, default=False)
    is_recharge: Mapped[bool] = mapped_column(Boolean, default=False)
    is_charge: Mapped[bool] = mapped_column(Boolean, default=False)
    is_protect: Mapped[bool] = mapped_column(Boolean, default=False)
    is_reflectable: Mapped[bool] = mapped_column(Boolean, default=False)
    is_snatchable: Mapped[bool] = mapped_column(Boolean, default=False)

    # Additional data
    flags: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Generation introduced
    generation: Mapped[int] = mapped_column(Integer, default=1)

    def __repr__(self) -> str:
        return f"<Move {self.id} {self.name}>"


class PokemonLearnset(Base):
    """Maps which Pokemon can learn which moves."""

    __tablename__ = "pokemon_learnsets"

    # Composite primary key
    species_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    move_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    learn_method: Mapped[str] = mapped_column(String(20), primary_key=True)

    # Level learned (for level-up moves)
    level_learned: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Version group (for generation-specific moves)
    version_group: Mapped[str | None] = mapped_column(String(30), nullable=True)

    def __repr__(self) -> str:
        return f"<PokemonLearnset {self.species_id} learns {self.move_id} via {self.learn_method}>"
