"""Script to import Pokemon data from PokeAPI."""

import asyncio
import json
from pathlib import Path

import httpx

# PokeAPI base URL
BASE_URL = "https://pokeapi.co/api/v2"

# Data directory
DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)


async def fetch_with_retry(client: httpx.AsyncClient, url: str, retries: int = 3) -> dict | None:
    """Fetch URL with retries."""
    for attempt in range(retries):
        try:
            response = await client.get(url, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            if attempt == retries - 1:
                print(f"Failed to fetch {url}: {e}")
                return None
            await asyncio.sleep(1 * (attempt + 1))
    return None


async def fetch_all_pokemon(client: httpx.AsyncClient, limit: int = 1025) -> list[dict]:
    """Fetch all Pokemon species data."""
    print(f"Fetching {limit} Pokemon species...")

    # Get list of all Pokemon
    list_url = f"{BASE_URL}/pokemon-species?limit={limit}"
    list_data = await fetch_with_retry(client, list_url)

    if not list_data:
        return []

    pokemon_list = []
    total = len(list_data["results"])

    for i, item in enumerate(list_data["results"]):
        if (i + 1) % 50 == 0:
            print(f"Progress: {i + 1}/{total}")

        # Fetch species data
        species_data = await fetch_with_retry(client, item["url"])
        if not species_data:
            continue

        # Fetch Pokemon data for stats
        pokemon_url = f"{BASE_URL}/pokemon/{species_data['id']}"
        pokemon_data = await fetch_with_retry(client, pokemon_url)

        if not pokemon_data:
            continue

        # Extract relevant data
        pokemon = {
            "national_dex": species_data["id"],
            "name": species_data["name"].replace("-", " ").title(),
            "name_lower": species_data["name"].lower(),
            # Types
            "type1": pokemon_data["types"][0]["type"]["name"],
            "type2": pokemon_data["types"][1]["type"]["name"] if len(pokemon_data["types"]) > 1 else None,
            # Base stats
            "base_hp": next(s["base_stat"] for s in pokemon_data["stats"] if s["stat"]["name"] == "hp"),
            "base_attack": next(s["base_stat"] for s in pokemon_data["stats"] if s["stat"]["name"] == "attack"),
            "base_defense": next(s["base_stat"] for s in pokemon_data["stats"] if s["stat"]["name"] == "defense"),
            "base_sp_attack": next(s["base_stat"] for s in pokemon_data["stats"] if s["stat"]["name"] == "special-attack"),
            "base_sp_defense": next(s["base_stat"] for s in pokemon_data["stats"] if s["stat"]["name"] == "special-defense"),
            "base_speed": next(s["base_stat"] for s in pokemon_data["stats"] if s["stat"]["name"] == "speed"),
            # Abilities
            "abilities": [a["ability"]["name"].replace("-", " ").title() for a in pokemon_data["abilities"] if not a["is_hidden"]],
            "hidden_ability": next((a["ability"]["name"].replace("-", " ").title() for a in pokemon_data["abilities"] if a["is_hidden"]), None),
            # Catch mechanics
            "catch_rate": species_data["capture_rate"],
            "base_friendship": species_data["base_happiness"] or 70,
            "base_experience": pokemon_data["base_experience"] or 64,
            # Growth
            "growth_rate": species_data["growth_rate"]["name"] if species_data["growth_rate"] else "medium",
            # Gender
            "gender_ratio": None if species_data["gender_rate"] == -1 else species_data["gender_rate"] * 12.5,
            # Breeding
            "egg_groups": [g["name"] for g in species_data["egg_groups"]],
            "hatch_counter": species_data["hatch_counter"] or 20,
            # Evolution
            "evolution_chain_id": int(species_data["evolution_chain"]["url"].split("/")[-2]) if species_data["evolution_chain"] else None,
            "evolves_from_species_id": species_data["evolves_from_species"]["url"].split("/")[-2] if species_data["evolves_from_species"] else None,
            # Sprites
            "sprite_url": pokemon_data["sprites"]["front_default"],
            "sprite_shiny_url": pokemon_data["sprites"]["front_shiny"],
            "sprite_back_url": pokemon_data["sprites"]["back_default"],
            "sprite_back_shiny_url": pokemon_data["sprites"]["back_shiny"],
            # Generation
            "generation": int(species_data["generation"]["url"].split("/")[-2]) if species_data["generation"] else 1,
            "is_legendary": species_data["is_legendary"],
            "is_mythical": species_data["is_mythical"],
            "is_baby": species_data["is_baby"],
            # Physical
            "height": pokemon_data["height"],
            "weight": pokemon_data["weight"],
            # Flavor text (English)
            "flavor_text": next(
                (f["flavor_text"].replace("\n", " ").replace("\f", " ")
                 for f in species_data["flavor_text_entries"]
                 if f["language"]["name"] == "en"),
                None
            ),
        }

        pokemon_list.append(pokemon)

    return pokemon_list


async def fetch_all_moves(client: httpx.AsyncClient, limit: int = 1000) -> list[dict]:
    """Fetch all moves data."""
    print(f"Fetching {limit} moves...")

    list_url = f"{BASE_URL}/move?limit={limit}"
    list_data = await fetch_with_retry(client, list_url)

    if not list_data:
        return []

    moves_list = []
    total = len(list_data["results"])

    for i, item in enumerate(list_data["results"]):
        if (i + 1) % 100 == 0:
            print(f"Progress: {i + 1}/{total}")

        move_data = await fetch_with_retry(client, item["url"])
        if not move_data:
            continue

        move = {
            "id": move_data["id"],
            "name": move_data["name"].replace("-", " ").title(),
            "name_lower": move_data["name"].lower(),
            "type": move_data["type"]["name"],
            "category": move_data["damage_class"]["name"] if move_data["damage_class"] else "status",
            "power": move_data["power"],
            "accuracy": move_data["accuracy"],
            "pp": move_data["pp"] or 20,
            "priority": move_data["priority"],
            "effect": next(
                (e["effect"] for e in move_data["effect_entries"] if e["language"]["name"] == "en"),
                None
            ),
            "effect_chance": move_data["effect_chance"],
            "target": move_data["target"]["name"] if move_data["target"] else "selected-pokemon",
            "generation": int(move_data["generation"]["url"].split("/")[-2]) if move_data["generation"] else 1,
            "description": next(
                (f["flavor_text"].replace("\n", " ") for f in move_data["flavor_text_entries"] if f["language"]["name"] == "en"),
                None
            ),
        }

        moves_list.append(move)

    return moves_list


async def fetch_all_abilities(client: httpx.AsyncClient, limit: int = 400) -> list[dict]:
    """Fetch all abilities data."""
    print(f"Fetching {limit} abilities...")

    list_url = f"{BASE_URL}/ability?limit={limit}"
    list_data = await fetch_with_retry(client, list_url)

    if not list_data:
        return []

    abilities_list = []
    total = len(list_data["results"])

    for i, item in enumerate(list_data["results"]):
        if (i + 1) % 50 == 0:
            print(f"Progress: {i + 1}/{total}")

        ability_data = await fetch_with_retry(client, item["url"])
        if not ability_data:
            continue

        ability = {
            "id": ability_data["id"],
            "name": ability_data["name"].replace("-", " ").title(),
            "name_lower": ability_data["name"].lower(),
            "effect": next(
                (e["effect"] for e in ability_data["effect_entries"] if e["language"]["name"] == "en"),
                None
            ),
            "short_effect": next(
                (e["short_effect"] for e in ability_data["effect_entries"] if e["language"]["name"] == "en"),
                None
            ),
            "generation": int(ability_data["generation"]["url"].split("/")[-2]) if ability_data["generation"] else 1,
        }

        abilities_list.append(ability)

    return abilities_list


async def fetch_all_items(client: httpx.AsyncClient, limit: int = 500) -> list[dict]:
    """Fetch relevant items (evolution items, held items)."""
    print(f"Fetching items...")

    # Relevant item categories
    categories = [
        "evolution",
        "held-items",
        "medicine",
        "vitamins",
        "type-enhancement",
    ]

    items_list = []

    for category in categories:
        cat_url = f"{BASE_URL}/item-category/{category}"
        cat_data = await fetch_with_retry(client, cat_url)

        if not cat_data:
            continue

        for item_ref in cat_data["items"]:
            item_data = await fetch_with_retry(client, item_ref["url"])
            if not item_data:
                continue

            item = {
                "id": item_data["id"],
                "name": item_data["name"].replace("-", " ").title(),
                "name_lower": item_data["name"].lower(),
                "category": category,
                "cost": item_data["cost"],
                "effect": next(
                    (e["effect"] for e in item_data["effect_entries"] if e["language"]["name"] == "en"),
                    None
                ),
                "short_effect": next(
                    (e["short_effect"] for e in item_data["effect_entries"] if e["language"]["name"] == "en"),
                    None
                ),
                "sprite_url": item_data["sprites"]["default"],
            }

            items_list.append(item)

    return items_list


async def main():
    """Main function to fetch and save all Pokemon data."""
    print("Starting Pokemon data import from PokeAPI...")
    print("This may take 15-30 minutes depending on connection speed.\n")

    async with httpx.AsyncClient() as client:
        # Fetch Pokemon
        pokemon = await fetch_all_pokemon(client)
        if pokemon:
            with open(DATA_DIR / "pokemon.json", "w") as f:
                json.dump(pokemon, f, indent=2)
            print(f"Saved {len(pokemon)} Pokemon to data/pokemon.json\n")

        # Fetch Moves
        moves = await fetch_all_moves(client)
        if moves:
            with open(DATA_DIR / "moves.json", "w") as f:
                json.dump(moves, f, indent=2)
            print(f"Saved {len(moves)} moves to data/moves.json\n")

        # Fetch Abilities
        abilities = await fetch_all_abilities(client)
        if abilities:
            with open(DATA_DIR / "abilities.json", "w") as f:
                json.dump(abilities, f, indent=2)
            print(f"Saved {len(abilities)} abilities to data/abilities.json\n")

        # Fetch Items
        items = await fetch_all_items(client)
        if items:
            with open(DATA_DIR / "items.json", "w") as f:
                json.dump(items, f, indent=2)
            print(f"Saved {len(items)} items to data/items.json\n")

    print("Data import complete!")


if __name__ == "__main__":
    asyncio.run(main())
