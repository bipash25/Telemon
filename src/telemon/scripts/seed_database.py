"""Seed database with initial data."""

import asyncio
import json
from pathlib import Path

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert

from telemon.database import async_session_factory, init_db
from telemon.database.models import Item, PokemonSpecies
from telemon.logging import get_logger, setup_logging

logger = get_logger(__name__)


SHOP_ITEMS = [
    # Evolution Stones
    {"id": 1, "name": "Fire Stone", "name_lower": "fire stone", "category": "evolution", "cost": 500, "sell_price": 250, "is_consumable": True, "is_holdable": False},
    {"id": 2, "name": "Water Stone", "name_lower": "water stone", "category": "evolution", "cost": 500, "sell_price": 250, "is_consumable": True, "is_holdable": False},
    {"id": 3, "name": "Thunder Stone", "name_lower": "thunder stone", "category": "evolution", "cost": 500, "sell_price": 250, "is_consumable": True, "is_holdable": False},
    {"id": 4, "name": "Leaf Stone", "name_lower": "leaf stone", "category": "evolution", "cost": 500, "sell_price": 250, "is_consumable": True, "is_holdable": False},
    {"id": 5, "name": "Moon Stone", "name_lower": "moon stone", "category": "evolution", "cost": 500, "sell_price": 250, "is_consumable": True, "is_holdable": False},
    {"id": 6, "name": "Sun Stone", "name_lower": "sun stone", "category": "evolution", "cost": 500, "sell_price": 250, "is_consumable": True, "is_holdable": False},
    {"id": 7, "name": "Dusk Stone", "name_lower": "dusk stone", "category": "evolution", "cost": 500, "sell_price": 250, "is_consumable": True, "is_holdable": False},
    {"id": 8, "name": "Dawn Stone", "name_lower": "dawn stone", "category": "evolution", "cost": 500, "sell_price": 250, "is_consumable": True, "is_holdable": False},
    {"id": 9, "name": "Shiny Stone", "name_lower": "shiny stone", "category": "evolution", "cost": 500, "sell_price": 250, "is_consumable": True, "is_holdable": False},
    {"id": 10, "name": "Ice Stone", "name_lower": "ice stone", "category": "evolution", "cost": 500, "sell_price": 250, "is_consumable": True, "is_holdable": False},
    # Battle Items
    {"id": 101, "name": "Leftovers", "name_lower": "leftovers", "category": "battle", "cost": 1000, "sell_price": 500, "is_consumable": False, "is_holdable": True},
    {"id": 102, "name": "Choice Band", "name_lower": "choice band", "category": "battle", "cost": 1500, "sell_price": 750, "is_consumable": False, "is_holdable": True},
    {"id": 103, "name": "Choice Specs", "name_lower": "choice specs", "category": "battle", "cost": 1500, "sell_price": 750, "is_consumable": False, "is_holdable": True},
    {"id": 104, "name": "Choice Scarf", "name_lower": "choice scarf", "category": "battle", "cost": 1500, "sell_price": 750, "is_consumable": False, "is_holdable": True},
    {"id": 105, "name": "Life Orb", "name_lower": "life orb", "category": "battle", "cost": 2000, "sell_price": 1000, "is_consumable": False, "is_holdable": True},
    {"id": 106, "name": "Focus Sash", "name_lower": "focus sash", "category": "battle", "cost": 1000, "sell_price": 500, "is_consumable": False, "is_holdable": True},
    {"id": 107, "name": "Assault Vest", "name_lower": "assault vest", "category": "battle", "cost": 1500, "sell_price": 750, "is_consumable": False, "is_holdable": True},
    {"id": 108, "name": "Rocky Helmet", "name_lower": "rocky helmet", "category": "battle", "cost": 1000, "sell_price": 500, "is_consumable": False, "is_holdable": True},
    # Utility Items
    {"id": 201, "name": "Rare Candy", "name_lower": "rare candy", "category": "utility", "cost": 200, "sell_price": 100, "is_consumable": True, "is_holdable": False},
    {"id": 202, "name": "Incense", "name_lower": "incense", "category": "utility", "cost": 500, "sell_price": 250, "is_consumable": True, "is_holdable": False},
    {"id": 203, "name": "XP Boost", "name_lower": "xp boost", "category": "utility", "cost": 300, "sell_price": 150, "is_consumable": True, "is_holdable": False},
    # Special Items
    {"id": 301, "name": "Shiny Charm", "name_lower": "shiny charm", "category": "special", "cost": 50000, "sell_price": 25000, "is_consumable": False, "is_holdable": False, "description": "Triples your shiny odds! A must-have for shiny hunters."},
    {"id": 302, "name": "Oval Charm", "name_lower": "oval charm", "category": "special", "cost": 25000, "sell_price": 12500, "is_consumable": False, "is_holdable": False, "description": "Increases egg hatch speed."},
]


async def seed_items() -> None:
    """Seed the items table."""
    async with async_session_factory() as session:
        for item_data in SHOP_ITEMS:
            stmt = insert(Item).values(**item_data).on_conflict_do_nothing(index_elements=["id"])
            await session.execute(stmt)
        await session.commit()
        logger.info("Seeded items table", count=len(SHOP_ITEMS))


async def seed_pokemon() -> None:
    """Seed Pokemon species from JSON file."""
    data_path = Path(__file__).parent.parent / "data" / "pokemon.json"
    
    if not data_path.exists():
        logger.warning("Pokemon data file not found", path=str(data_path))
        return

    with open(data_path) as f:
        pokemon_data = json.load(f)

    async with async_session_factory() as session:
        # Check if already seeded
        result = await session.execute(select(PokemonSpecies).limit(1))
        if result.scalar_one_or_none():
            logger.info("Pokemon already seeded, skipping")
            return

        for poke in pokemon_data:
            species = PokemonSpecies(**poke)
            session.add(species)

        await session.commit()
        logger.info("Seeded Pokemon species", count=len(pokemon_data))


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
