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
    data_path = Path(__file__).parent.parent.parent.parent / "data" / "pokemon.json"
    
    if not data_path.exists():
        logger.warning("Pokemon data file not found", path=str(data_path))
        return

    with open(data_path) as f:
        pokemon_data = json.load(f)

    async with async_session_factory() as session:
        # Count existing Pokemon
        result = await session.execute(text("SELECT COUNT(*) FROM pokemon_species"))
        existing_count = result.scalar()
        
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
        new_count = result.scalar()
        
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
