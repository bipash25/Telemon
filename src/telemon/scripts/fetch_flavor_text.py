"""Fetch Pokedex flavor text + genus from PokeAPI and update DB.

Usage:
    python -m telemon.scripts.fetch_flavor_text

Fetches English flavor text entries and genus (category) for all 1025 species
from the PokeAPI pokemon-species endpoint, then updates the `flavor_text`
column in the `pokemon_species` table.
"""

import asyncio
import sys
from pathlib import Path

import aiohttp
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from telemon.database.models.species import PokemonSpecies


DATABASE_URL = "postgresql+asyncpg://telemon:telemon@localhost:5434/telemon"
POKEAPI_BASE = "https://pokeapi.co/api/v2/pokemon-species"
TOTAL_SPECIES = 1025
BATCH_SIZE = 25  # concurrent requests per batch
HEADERS = {"User-Agent": "Telemon-Bot/1.0 (+https://github.com/bipash25/Telemon)"}


def clean_text(raw: str) -> str:
    """Clean PokeAPI flavor text (remove control chars, collapse whitespace)."""
    return raw.replace("\f", " ").replace("\n", " ").replace("\r", " ").replace("  ", " ").strip()


async def fetch_species(
    http: aiohttp.ClientSession, dex_num: int
) -> tuple[int, str | None, str | None]:
    """Fetch flavor text and genus for one species. Returns (dex, flavor, genus)."""
    url = f"{POKEAPI_BASE}/{dex_num}"
    try:
        async with http.get(url) as resp:
            if resp.status != 200:
                print(f"  [WARN] #{dex_num}: HTTP {resp.status}")
                return dex_num, None, None

            data = await resp.json()

            # Get English flavor text — prefer latest game version
            en_texts = [
                e for e in data.get("flavor_text_entries", [])
                if e.get("language", {}).get("name") == "en"
            ]
            flavor = None
            if en_texts:
                # Pick the last (most recent) English entry
                flavor = clean_text(en_texts[-1]["flavor_text"])

            # Get English genus (e.g. "Seed Pokémon")
            genus = None
            en_genera = [
                g for g in data.get("genera", [])
                if g.get("language", {}).get("name") == "en"
            ]
            if en_genera:
                genus = en_genera[0]["genus"]

            return dex_num, flavor, genus

    except Exception as e:
        print(f"  [ERR] #{dex_num}: {e}")
        return dex_num, None, None


async def main() -> None:
    engine = create_async_engine(DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    print(f"Fetching flavor text for {TOTAL_SPECIES} species from PokeAPI...")
    print(f"Batch size: {BATCH_SIZE} concurrent requests\n")

    results: dict[int, tuple[str | None, str | None]] = {}

    async with aiohttp.ClientSession(headers=HEADERS) as http:
        for batch_start in range(1, TOTAL_SPECIES + 1, BATCH_SIZE):
            batch_end = min(batch_start + BATCH_SIZE, TOTAL_SPECIES + 1)
            batch_ids = list(range(batch_start, batch_end))

            tasks = [fetch_species(http, dex) for dex in batch_ids]
            batch_results = await asyncio.gather(*tasks)

            for dex_num, flavor, genus in batch_results:
                results[dex_num] = (flavor, genus)

            fetched = min(batch_end - 1, TOTAL_SPECIES)
            pct = fetched / TOTAL_SPECIES * 100
            print(f"  Fetched {fetched}/{TOTAL_SPECIES} ({pct:.0f}%)")

            # Rate limit: small delay between batches
            if batch_end <= TOTAL_SPECIES:
                await asyncio.sleep(1.0)

    # Count successes
    have_flavor = sum(1 for f, g in results.values() if f)
    have_genus = sum(1 for f, g in results.values() if g)
    print(f"\nFetched: {have_flavor} flavor texts, {have_genus} genera")

    # Combine flavor + genus into a single display string
    # Format: "The Seed Pokémon. A strange seed was planted on its back..."
    combined: dict[int, str] = {}
    for dex_num, (flavor, genus) in results.items():
        parts = []
        if genus:
            parts.append(f"The {genus}.")
        if flavor:
            parts.append(flavor)
        if parts:
            combined[dex_num] = " ".join(parts)

    # Update DB
    print(f"Updating {len(combined)} species in database...")

    async with async_session() as session:
        updated = 0
        for dex_num, text in combined.items():
            await session.execute(
                update(PokemonSpecies)
                .where(PokemonSpecies.national_dex == dex_num)
                .values(flavor_text=text)
            )
            updated += 1

        await session.commit()
        print(f"Updated {updated} species with flavor text.")

    await engine.dispose()
    print("Done!")


if __name__ == "__main__":
    asyncio.run(main())
