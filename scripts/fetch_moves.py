"""Fetch moves and learnsets from PokeAPI.

Fetches:
1. All Pokemon endpoints to get learnset data (which moves each species learns)
2. All unique move endpoints for move details (power, type, accuracy, etc.)

Saves to:
- data/moves.json — Move details
- data/learnsets.json — Species -> level-up moves mapping
"""

import asyncio
import json
import sys
from pathlib import Path

import aiohttp

BASE_URL = "https://pokeapi.co/api/v2"
MAX_SPECIES = 1025
CONCURRENCY = 30  # concurrent requests

# We only care about the latest version group for learnsets
# "scarlet-violet" is version-group 25
TARGET_VERSION_GROUPS = [
    "scarlet-violet",
    "sword-shield",
    "ultra-sun-ultra-moon",
    "sun-moon",
    "omega-ruby-alpha-sapphire",
    "x-y",
    "black-2-white-2",
    "black-white",
]


async def fetch_json(session: aiohttp.ClientSession, url: str, sem: asyncio.Semaphore) -> dict | None:
    """Fetch JSON from URL with semaphore for rate limiting."""
    async with sem:
        for attempt in range(3):
            try:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    elif resp.status == 404:
                        return None
                    else:
                        print(f"  HTTP {resp.status} for {url}, retrying...")
                        await asyncio.sleep(1)
            except Exception as e:
                print(f"  Error fetching {url}: {e}, retrying...")
                await asyncio.sleep(2)
    return None


async def fetch_pokemon_moves(session: aiohttp.ClientSession, sem: asyncio.Semaphore, dex_num: int) -> dict | None:
    """Fetch a single Pokemon's move data."""
    data = await fetch_json(session, f"{BASE_URL}/pokemon/{dex_num}", sem)
    if not data:
        return None

    # Extract level-up moves from the best available version group
    level_up_moves = []
    
    for move_entry in data.get("moves", []):
        move_name = move_entry["move"]["name"]
        move_url = move_entry["move"]["url"]
        move_id = int(move_url.rstrip("/").split("/")[-1])

        # Find level-up learn method in best available version
        best_version = None
        best_level = None

        for vg_detail in move_entry.get("version_group_details", []):
            if vg_detail["move_learn_method"]["name"] == "level-up":
                vg_name = vg_detail["version_group"]["name"]
                level = vg_detail["level_learned_at"]

                # Prefer latest version group
                for target_vg in TARGET_VERSION_GROUPS:
                    if vg_name == target_vg:
                        if best_version is None or TARGET_VERSION_GROUPS.index(vg_name) < TARGET_VERSION_GROUPS.index(best_version):
                            best_version = vg_name
                            best_level = level
                        break

        if best_version is not None and best_level is not None:
            level_up_moves.append({
                "move_id": move_id,
                "move_name": move_name,
                "level": best_level,
            })

    # Sort by level
    level_up_moves.sort(key=lambda m: m["level"])

    return {
        "species_id": dex_num,
        "level_up_moves": level_up_moves,
    }


async def fetch_move_details(session: aiohttp.ClientSession, sem: asyncio.Semaphore, move_id: int) -> dict | None:
    """Fetch details for a single move."""
    data = await fetch_json(session, f"{BASE_URL}/move/{move_id}", sem)
    if not data:
        return None

    # Get English flavor text
    description = ""
    for entry in data.get("flavor_text_entries", []):
        if entry["language"]["name"] == "en":
            description = entry["flavor_text"].replace("\n", " ").replace("\f", " ")
            break

    # Get English effect
    effect = ""
    for entry in data.get("effect_entries", []):
        if entry["language"]["name"] == "en":
            effect = entry["short_effect"]
            break

    return {
        "id": data["id"],
        "name": data["name"].replace("-", " ").title(),
        "name_lower": data["name"].replace("-", " ").lower(),
        "type": data["type"]["name"],
        "category": data["damage_class"]["name"],  # physical, special, status
        "power": data["power"],
        "accuracy": data["accuracy"],
        "pp": data["pp"],
        "priority": data["priority"],
        "effect": effect,
        "effect_chance": data["effect_chance"],
        "description": description,
        "generation": int(data["generation"]["url"].rstrip("/").split("/")[-1]),
        "makes_contact": False,  # Simplified — contact flag not consistently available
        "crit_rate": (data.get("meta") or {}).get("crit_rate", 0) or 0,
    }


async def main():
    data_dir = Path(__file__).parent.parent / "data"
    data_dir.mkdir(exist_ok=True)

    sem = asyncio.Semaphore(CONCURRENCY)

    async with aiohttp.ClientSession() as session:
        # Step 1: Fetch all Pokemon move data
        print(f"Fetching move data for {MAX_SPECIES} Pokemon...")
        tasks = [
            fetch_pokemon_moves(session, sem, i)
            for i in range(1, MAX_SPECIES + 1)
        ]

        results = []
        batch_size = 100
        for batch_start in range(0, len(tasks), batch_size):
            batch = tasks[batch_start:batch_start + batch_size]
            batch_results = await asyncio.gather(*batch)
            results.extend(batch_results)
            done = min(batch_start + batch_size, len(tasks))
            print(f"  Progress: {done}/{MAX_SPECIES} Pokemon fetched")

        # Filter successful results
        learnsets = [r for r in results if r is not None]
        print(f"  Got learnsets for {len(learnsets)} Pokemon")

        # Step 2: Collect unique move IDs
        unique_move_ids = set()
        for ls in learnsets:
            for move in ls["level_up_moves"]:
                unique_move_ids.add(move["move_id"])

        print(f"\nFetching details for {len(unique_move_ids)} unique moves...")

        # Step 3: Fetch move details
        move_tasks = [
            fetch_move_details(session, sem, mid)
            for mid in sorted(unique_move_ids)
        ]

        move_results = []
        for batch_start in range(0, len(move_tasks), batch_size):
            batch = move_tasks[batch_start:batch_start + batch_size]
            batch_results = await asyncio.gather(*batch)
            move_results.extend(batch_results)
            done = min(batch_start + batch_size, len(move_tasks))
            print(f"  Progress: {done}/{len(unique_move_ids)} moves fetched")

        moves = [m for m in move_results if m is not None]
        print(f"  Got details for {len(moves)} moves")

    # Step 4: Save to JSON
    moves_path = data_dir / "moves.json"
    learnsets_path = data_dir / "learnsets.json"

    with open(moves_path, "w") as f:
        json.dump(moves, f, indent=2)
    print(f"\nSaved {len(moves)} moves to {moves_path}")

    with open(learnsets_path, "w") as f:
        json.dump(learnsets, f, indent=2)
    print(f"Saved {len(learnsets)} learnsets to {learnsets_path}")

    # Stats
    total_learnset_entries = sum(len(ls["level_up_moves"]) for ls in learnsets)
    print(f"\nTotal learnset entries: {total_learnset_entries}")
    print(f"Average moves per species: {total_learnset_entries / len(learnsets):.1f}")

    # Category breakdown
    cats = {}
    for m in moves:
        cat = m["category"]
        cats[cat] = cats.get(cat, 0) + 1
    print(f"Move categories: {cats}")

    # Type breakdown
    types = {}
    for m in moves:
        t = m["type"]
        types[t] = types.get(t, 0) + 1
    print(f"Move types: {dict(sorted(types.items()))}")


if __name__ == "__main__":
    asyncio.run(main())
