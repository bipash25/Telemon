"""Pokemon species model - static data for all Pokemon."""

from sqlalchemy import Boolean, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from telemon.database.models.base import Base


class PokemonSpecies(Base):
    """Static data for a Pokemon species."""

    __tablename__ = "pokemon_species"

    # National Pokedex number
    national_dex: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Basic info
    name: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    name_lower: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    # Types
    type1: Mapped[str] = mapped_column(String(20), nullable=False)
    type2: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Base stats
    base_hp: Mapped[int] = mapped_column(Integer, nullable=False)
    base_attack: Mapped[int] = mapped_column(Integer, nullable=False)
    base_defense: Mapped[int] = mapped_column(Integer, nullable=False)
    base_sp_attack: Mapped[int] = mapped_column(Integer, nullable=False)
    base_sp_defense: Mapped[int] = mapped_column(Integer, nullable=False)
    base_speed: Mapped[int] = mapped_column(Integer, nullable=False)

    # Abilities (list of ability names)
    abilities: Mapped[list] = mapped_column(ARRAY(String(50)), default=list)
    hidden_ability: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Catch mechanics
    catch_rate: Mapped[int] = mapped_column(Integer, default=45)
    base_friendship: Mapped[int] = mapped_column(Integer, default=70)
    base_experience: Mapped[int] = mapped_column(Integer, default=64)

    # Growth
    growth_rate: Mapped[str] = mapped_column(String(30), default="medium")

    # Gender
    gender_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)  # Female ratio, None = genderless

    # Breeding
    egg_groups: Mapped[list] = mapped_column(ARRAY(String(30)), default=list)
    hatch_counter: Mapped[int] = mapped_column(Integer, default=20)

    # Evolution
    evolution_chain_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    evolves_from_species_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Sprites
    sprite_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    sprite_shiny_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    sprite_back_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    sprite_back_shiny_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Generation and categories
    generation: Mapped[int] = mapped_column(Integer, default=1)
    is_legendary: Mapped[bool] = mapped_column(Boolean, default=False)
    is_mythical: Mapped[bool] = mapped_column(Boolean, default=False)
    is_baby: Mapped[bool] = mapped_column(Boolean, default=False)

    # Physical characteristics
    height: Mapped[int] = mapped_column(Integer, default=10)  # In decimeters
    weight: Mapped[int] = mapped_column(Integer, default=100)  # In hectograms

    # Additional data (JSON for flexibility)
    forms: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    flavor_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<PokemonSpecies #{self.national_dex} {self.name}>"

    @property
    def types(self) -> list[str]:
        """Get list of types."""
        if self.type2:
            return [self.type1, self.type2]
        return [self.type1]

    @property
    def base_stat_total(self) -> int:
        """Get base stat total."""
        return (
            self.base_hp
            + self.base_attack
            + self.base_defense
            + self.base_sp_attack
            + self.base_sp_defense
            + self.base_speed
        )

    @property
    def rarity(self) -> str:
        """Get rarity based on catch rate and legendary status."""
        if self.is_mythical:
            return "mythical"
        if self.is_legendary:
            return "legendary"
        if self.catch_rate <= 3:
            return "ultra_rare"
        if self.catch_rate <= 45:
            return "rare"
        if self.catch_rate <= 120:
            return "uncommon"
        return "common"
