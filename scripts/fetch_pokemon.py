#!/usr/bin/env python3
"""Fetch Pokemon data from PokeAPI for all generations."""

import asyncio
import json
import sys
from pathlib import Path

import httpx

# PokeAPI base URL
POKEAPI_BASE = "https://pokeapi.co/api/v2"

# Generation ranges
GENERATIONS = {
    2: (152, 251),   # Johto
    3: (252, 386),   # Hoenn
    4: (387, 493),   # Sinnoh
    5: (494, 649),   # Unova
    6: (650, 721),   # Kalos
    7: (722, 809),   # Alola
    8: (810, 905),   # Galar
    9: (906, 1025),  # Paldea
}


async def fetch_pokemon(client: httpx.AsyncClient, dex_num: int) -> dict | None:
    """Fetch a single Pokemon's data from PokeAPI."""
    try:
        # Get pokemon data
        pokemon_resp = await client.get(f"{POKEAPI_BASE}/pokemon/{dex_num}")
        if pokemon_resp.status_code != 200:
            print(f"  Failed to fetch Pokemon #{dex_num}: {pokemon_resp.status_code}")
            return None
        
        pokemon_data = pokemon_resp.json()
        
        # Get species data for additional info
        species_resp = await client.get(f"{POKEAPI_BASE}/pokemon-species/{dex_num}")
        if species_resp.status_code != 200:
            print(f"  Failed to fetch species #{dex_num}: {species_resp.status_code}")
            return None
        
        species_data = species_resp.json()
        
        # Extract types
        types = [t["type"]["name"] for t in pokemon_data["types"]]
        type1 = types[0] if types else "normal"
        type2 = types[1] if len(types) > 1 else None
        
        # Extract stats
        stats = {s["stat"]["name"]: s["base_stat"] for s in pokemon_data["stats"]}
        
        # Extract abilities
        abilities = []
        hidden_ability = None
        for ability in pokemon_data["abilities"]:
            ability_name = ability["ability"]["name"].replace("-", " ").title()
            if ability["is_hidden"]:
                hidden_ability = ability_name
            else:
                abilities.append(ability_name)
        
        # Get evolution chain ID from URL
        evolution_chain_url = species_data.get("evolution_chain", {}).get("url", "")
        evolution_chain_id = None
        if evolution_chain_url:
            # Extract ID from URL like https://pokeapi.co/api/v2/evolution-chain/1/
            parts = evolution_chain_url.rstrip("/").split("/")
            evolution_chain_id = int(parts[-1]) if parts[-1].isdigit() else None
        
        # Get egg groups
        egg_groups = [eg["name"] for eg in species_data.get("egg_groups", [])]
        
        # Build Pokemon object matching our format
        pokemon = {
            "national_dex": dex_num,
            "name": pokemon_data["name"].replace("-", " ").title(),
            "name_lower": pokemon_data["name"].lower(),
            "type1": type1,
            "type2": type2,
            "base_hp": stats.get("hp", 50),
            "base_attack": stats.get("attack", 50),
            "base_defense": stats.get("defense", 50),
            "base_sp_attack": stats.get("special-attack", 50),
            "base_sp_defense": stats.get("special-defense", 50),
            "base_speed": stats.get("speed", 50),
            "abilities": abilities,
            "hidden_ability": hidden_ability,
            "catch_rate": species_data.get("capture_rate", 45),
            "base_friendship": species_data.get("base_happiness", 70),
            "base_experience": pokemon_data.get("base_experience") or 64,
            "growth_rate": species_data.get("growth_rate", {}).get("name", "medium"),
            "gender_ratio": (8 - species_data.get("gender_rate", 4)) * 12.5 if species_data.get("gender_rate", -1) >= 0 else None,
            "egg_groups": egg_groups,
            "evolution_chain_id": evolution_chain_id,
            "sprite_url": f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/{dex_num}.png",
            "sprite_shiny_url": f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/shiny/{dex_num}.png",
            "generation": species_data.get("generation", {}).get("name", "generation-i").split("-")[-1],
            "is_legendary": species_data.get("is_legendary", False),
            "is_mythical": species_data.get("is_mythical", False),
            "is_baby": species_data.get("is_baby", False),
            "height": pokemon_data.get("height", 10),
            "weight": pokemon_data.get("weight", 100),
        }
        
        # Convert generation roman numeral to number
        gen_map = {"i": 1, "ii": 2, "iii": 3, "iv": 4, "v": 5, "vi": 6, "vii": 7, "viii": 8, "ix": 9}
        if isinstance(pokemon["generation"], str):
            pokemon["generation"] = gen_map.get(pokemon["generation"], 1)
        
        return pokemon
        
    except Exception as e:
        print(f"  Error fetching Pokemon #{dex_num}: {e}")
        return None


async def fetch_generation(gen: int, start: int, end: int) -> list[dict]:
    """Fetch all Pokemon for a generation."""
    print(f"\nFetching Generation {gen} (#{start}-#{end})...")
    
    pokemon_list = []
    
    # Use a semaphore to limit concurrent requests
    semaphore = asyncio.Semaphore(10)
    
    async def fetch_with_semaphore(client: httpx.AsyncClient, dex_num: int):
        async with semaphore:
            return await fetch_pokemon(client, dex_num)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        tasks = [fetch_with_semaphore(client, dex_num) for dex_num in range(start, end + 1)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, result in enumerate(results):
            dex_num = start + i
            if isinstance(result, Exception):
                print(f"  Exception for #{dex_num}: {result}")
            elif result:
                pokemon_list.append(result)
                if len(pokemon_list) % 10 == 0:
                    print(f"  Fetched {len(pokemon_list)}/{end - start + 1} Pokemon")
    
    print(f"  Completed Gen {gen}: {len(pokemon_list)} Pokemon")
    return pokemon_list


async def main():
    """Main function to fetch all Pokemon."""
    data_dir = Path(__file__).parent.parent / "data"
    
    # Load existing data
    existing_file = data_dir / "pokemon.json"
    if existing_file.exists():
        with open(existing_file) as f:
            existing_data = json.load(f)
        print(f"Loaded {len(existing_data)} existing Pokemon from pokemon.json")
    else:
        existing_data = []
        print("No existing pokemon.json found")
    
    all_pokemon = existing_data.copy()
    
    # Determine which generations to fetch
    gens_to_fetch = []
    if len(sys.argv) > 1:
        # Fetch specific generations
        for arg in sys.argv[1:]:
            if arg.isdigit():
                gen = int(arg)
                if gen in GENERATIONS:
                    gens_to_fetch.append(gen)
    else:
        # Fetch all generations 2-9
        gens_to_fetch = list(GENERATIONS.keys())
    
    print(f"\nWill fetch generations: {gens_to_fetch}")
    
    # Fetch each generation (remove any existing Pokemon from that range first)
    for gen in gens_to_fetch:
        start, end = GENERATIONS[gen]
        # Remove existing Pokemon in this range
        all_pokemon = [p for p in all_pokemon if not (start <= p["national_dex"] <= end)]
        gen_pokemon = await fetch_generation(gen, start, end)
        all_pokemon.extend(gen_pokemon)
    
    # Sort by national dex number
    all_pokemon.sort(key=lambda p: p["national_dex"])
    
    # Save to file
    output_file = data_dir / "pokemon.json"
    with open(output_file, "w") as f:
        json.dump(all_pokemon, f, indent=2)
    
    print(f"\nSaved {len(all_pokemon)} Pokemon to {output_file}")
    
    # Print stats
    print("\nPokemon per generation:")
    for gen in range(1, 10):
        count = len([p for p in all_pokemon if p.get("generation") == gen])
        print(f"  Gen {gen}: {count}")


if __name__ == "__main__":
    asyncio.run(main())
