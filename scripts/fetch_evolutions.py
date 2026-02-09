#!/usr/bin/env python3
"""Fetch evolution chain data from PokeAPI for all generations."""

import asyncio
import json
from pathlib import Path

import httpx

POKEAPI_BASE = "https://pokeapi.co/api/v2"

# Map evolution triggers to our format
TRIGGER_MAP = {
    "level-up": "level",
    "use-item": "item",
    "trade": "trade",
    "shed": "level",  # Special case for Shedinja
}

# Map item names to our format
ITEM_MAP = {
    "thunder-stone": "thunder stone",
    "fire-stone": "fire stone",
    "water-stone": "water stone",
    "leaf-stone": "leaf stone",
    "moon-stone": "moon stone",
    "sun-stone": "sun stone",
    "shiny-stone": "shiny stone",
    "dusk-stone": "dusk stone",
    "dawn-stone": "dawn stone",
    "ice-stone": "ice stone",
    "oval-stone": "oval stone",
    "kings-rock": "kings rock",
    "metal-coat": "metal coat",
    "dragon-scale": "dragon scale",
    "upgrade": "upgrade",
    "dubious-disc": "dubious disc",
    "protector": "protector",
    "electirizer": "electirizer",
    "magmarizer": "magmarizer",
    "reaper-cloth": "reaper cloth",
    "razor-claw": "razor claw",
    "razor-fang": "razor fang",
    "prism-scale": "prism scale",
    "whipped-dream": "whipped dream",
    "sachet": "sachet",
    "deep-sea-tooth": "deep sea tooth",
    "deep-sea-scale": "deep sea scale",
    "linking-cord": "linking cord",
    "black-augurite": "black augurite",
    "peat-block": "peat block",
    "auspicious-armor": "auspicious armor",
    "malicious-armor": "malicious armor",
    "chipped-pot": "chipped pot",
    "cracked-pot": "cracked pot",
    "galarica-cuff": "galarica cuff",
    "galarica-wreath": "galarica wreath",
    "scroll-of-darkness": "scroll of darkness",
    "scroll-of-waters": "scroll of waters",
    "sweet-apple": "sweet apple",
    "tart-apple": "tart apple",
    "strawberry-sweet": "sweet",
    "syrup-apple": "syrup apple",
    "unremarkable-teacup": "teacup",
    "masterpiece-teacup": "teacup",
}


def extract_species_id(url: str) -> int:
    """Extract species ID from URL."""
    return int(url.rstrip("/").split("/")[-1])


def process_evolution_details(details: list) -> dict:
    """Process evolution details into our format."""
    if not details:
        return {"trigger": "level", "min_level": 1}
    
    detail = details[0]  # Take first evolution method
    trigger_type = detail.get("trigger", {}).get("name", "level-up")
    
    result = {"trigger": TRIGGER_MAP.get(trigger_type, "level")}
    
    # Handle level-up evolution
    if trigger_type == "level-up":
        min_level = detail.get("min_level")
        if min_level:
            result["min_level"] = min_level
        else:
            # Special conditions - treat as level 20 if no level specified
            result["min_level"] = 20
            
        # Check for friendship evolution
        min_happiness = detail.get("min_happiness")
        if min_happiness:
            result["trigger"] = "friendship"
            result["min_happiness"] = min_happiness
    
    # Handle item evolution
    elif trigger_type == "use-item":
        item = detail.get("item", {}).get("name", "")
        result["item"] = ITEM_MAP.get(item, item.replace("-", " "))
    
    # Handle trade evolution
    elif trigger_type == "trade":
        held_item = detail.get("held_item")
        if held_item:
            item_name = held_item.get("name", "")
            result["item"] = ITEM_MAP.get(item_name, item_name.replace("-", " "))
    
    return result


def traverse_chain(chain_data: dict, evolutions: list) -> None:
    """Recursively traverse evolution chain."""
    species_id = extract_species_id(chain_data["species"]["url"])
    
    for evo in chain_data.get("evolves_to", []):
        evo_species_id = extract_species_id(evo["species"]["url"])
        evo_details = process_evolution_details(evo.get("evolution_details", []))
        
        evolution = {
            "species_id": species_id,
            "evolves_to": evo_species_id,
            **evo_details
        }
        evolutions.append(evolution)
        
        # Recursively process further evolutions
        traverse_chain(evo, evolutions)


async def fetch_evolution_chain(client: httpx.AsyncClient, chain_id: int) -> tuple[int, list]:
    """Fetch a single evolution chain."""
    try:
        resp = await client.get(f"{POKEAPI_BASE}/evolution-chain/{chain_id}")
        if resp.status_code != 200:
            return chain_id, []
        
        data = resp.json()
        evolutions = []
        traverse_chain(data["chain"], evolutions)
        return chain_id, evolutions
    except Exception as e:
        print(f"  Error fetching chain {chain_id}: {e}")
        return chain_id, []


async def main():
    """Main function to fetch all evolution chains."""
    data_dir = Path(__file__).parent.parent / "data"
    
    # Load existing evolution data
    existing_file = data_dir / "evolutions.json"
    if existing_file.exists():
        with open(existing_file) as f:
            existing_data = json.load(f)
        print(f"Loaded {len(existing_data)} existing evolution chains")
    else:
        existing_data = {}
    
    # Load Pokemon data to get evolution chain IDs
    pokemon_file = data_dir / "pokemon.json"
    with open(pokemon_file) as f:
        pokemon_data = json.load(f)
    
    # Get unique evolution chain IDs
    chain_ids = set()
    for pokemon in pokemon_data:
        chain_id = pokemon.get("evolution_chain_id")
        if chain_id:
            chain_ids.add(chain_id)
    
    print(f"Found {len(chain_ids)} unique evolution chains to fetch")
    
    # Only fetch chains we don't have
    existing_ids = set(int(k) for k in existing_data.keys())
    new_chain_ids = chain_ids - existing_ids
    print(f"Need to fetch {len(new_chain_ids)} new chains")
    
    if not new_chain_ids:
        print("All evolution chains already fetched!")
        return
    
    all_chains = dict(existing_data)
    
    # Fetch evolution chains
    semaphore = asyncio.Semaphore(10)
    
    async def fetch_with_semaphore(client: httpx.AsyncClient, chain_id: int):
        async with semaphore:
            return await fetch_evolution_chain(client, chain_id)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        tasks = [fetch_with_semaphore(client, chain_id) for chain_id in sorted(new_chain_ids)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        fetched = 0
        for result in results:
            if isinstance(result, Exception):
                print(f"  Exception: {result}")
                continue
            
            chain_id, evolutions = result
            if evolutions:
                all_chains[str(chain_id)] = {"chain": evolutions}
                fetched += 1
                if fetched % 50 == 0:
                    print(f"  Fetched {fetched} chains...")
    
    print(f"\nFetched {fetched} new evolution chains")
    
    # Save to file
    output_file = data_dir / "evolutions.json"
    with open(output_file, "w") as f:
        json.dump(all_chains, f, indent=2)
    
    print(f"Saved {len(all_chains)} total evolution chains to {output_file}")
    
    # Print stats
    total_evolutions = sum(len(c["chain"]) for c in all_chains.values())
    print(f"Total evolution entries: {total_evolutions}")


if __name__ == "__main__":
    asyncio.run(main())
