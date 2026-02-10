"""Seed database with initial data."""

import asyncio
import json
from pathlib import Path

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert

from telemon.core.items import ALL_ITEMS
from telemon.database import async_session_factory, init_db
from telemon.database.models import Item, PokemonSpecies
from telemon.logging import get_logger, setup_logging

logger = get_logger(__name__)


async def seed_items() -> None:
    """Seed the items table from the centralized catalog."""
    async with async_session_factory() as session:
        for item_data in ALL_ITEMS:
            # Only include fields the Item model has
            values = {
                "id": item_data["id"],
                "name": item_data["name"],
                "name_lower": item_data["name_lower"],
                "category": item_data["category"],
                "cost": item_data["cost"],
                "sell_price": item_data["sell_price"],
                "is_consumable": item_data.get("is_consumable", True),
                "is_holdable": item_data.get("is_holdable", False),
                "description": item_data.get("description"),
            }
            stmt = insert(Item).values(**values)
            stmt = stmt.on_conflict_do_update(
                index_elements=["id"],
                set_={
                    "name": values["name"],
                    "name_lower": values["name_lower"],
                    "category": values["category"],
                    "cost": values["cost"],
                    "sell_price": values["sell_price"],
                    "is_consumable": values["is_consumable"],
                    "is_holdable": values["is_holdable"],
                    "description": values["description"],
                },
            )
            await session.execute(stmt)
        await session.commit()
        logger.info("Seeded items table", count=len(ALL_ITEMS))


async def seed_pokemon() -> None:
    """Seed Pokemon species from JSON file."""
    data_path = Path(__file__).parent.parent.parent.parent / "data" / "pokemon.json"

    if not data_path.exists():
        logger.warning("Pokemon data file not found", path=str(data_path))
        return

    with open(data_path) as f:
        pokemon_data = json.load(f)

    async with async_session_factory() as session:
        # Count existing Pokemon
        result = await session.execute(text("SELECT COUNT(*) FROM pokemon_species"))
        existing_count = result.scalar() or 0

        logger.info(f"Found {existing_count} existing Pokemon, loading {len(pokemon_data)} from JSON")

        # Use upsert to add new Pokemon and update existing ones
        for poke in pokemon_data:
            stmt = insert(PokemonSpecies).values(**poke)
            stmt = stmt.on_conflict_do_update(
                index_elements=["national_dex"],
                set_={
                    "name": poke["name"],
                    "name_lower": poke["name_lower"],
                    "type1": poke["type1"],
                    "type2": poke.get("type2"),
                    "base_hp": poke["base_hp"],
                    "base_attack": poke["base_attack"],
                    "base_defense": poke["base_defense"],
                    "base_sp_attack": poke["base_sp_attack"],
                    "base_sp_defense": poke["base_sp_defense"],
                    "base_speed": poke["base_speed"],
                    "abilities": poke.get("abilities", []),
                    "hidden_ability": poke.get("hidden_ability"),
                    "catch_rate": poke.get("catch_rate", 45),
                    "base_friendship": poke.get("base_friendship", 70),
                    "base_experience": poke.get("base_experience", 64),
                    "growth_rate": poke.get("growth_rate", "medium"),
                    "gender_ratio": poke.get("gender_ratio"),
                    "egg_groups": poke.get("egg_groups", []),
                    "evolution_chain_id": poke.get("evolution_chain_id"),
                    "sprite_url": poke.get("sprite_url"),
                    "sprite_shiny_url": poke.get("sprite_shiny_url"),
                    "generation": poke.get("generation", 1),
                    "is_legendary": poke.get("is_legendary", False),
                    "is_mythical": poke.get("is_mythical", False),
                    "is_baby": poke.get("is_baby", False),
                    "height": poke.get("height", 10),
                    "weight": poke.get("weight", 100),
                }
            )
            await session.execute(stmt)

        await session.commit()

        # Count after seeding
        result = await session.execute(text("SELECT COUNT(*) FROM pokemon_species"))
        new_count = result.scalar() or 0

        logger.info("Seeded Pokemon species", before=existing_count, after=new_count, added=new_count - existing_count)


async def main() -> None:
    """Run all seed functions."""
    setup_logging()
    await init_db()

    logger.info("Starting database seeding...")

    await seed_items()
    await seed_pokemon()

    logger.info("Database seeding complete!")


if __name__ == "__main__":
    asyncio.run(main())
