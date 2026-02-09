"""Catching-related handlers."""

from datetime import datetime, timedelta

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message
from rapidfuzz import fuzz
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from telemon.database.models import ActiveSpawn, Group, Pokemon, PokedexEntry, User
from telemon.logging import get_logger

router = Router(name="catch")
logger = get_logger(__name__)

# Track last hint time per user per chat (simple in-memory cache)
# In production, use Redis for this
_hint_cooldowns: dict[tuple[int, int], datetime] = {}
HINT_COOLDOWN_SECONDS = 10


def generate_hint(name: str, hints_used: int) -> str:
    """Generate a hint showing some letters of the Pokemon name."""
    if hints_used == 0:
        # First hint: show length and first letter
        return f"{name[0]}{'_' * (len(name) - 1)} ({len(name)} letters)"
    elif hints_used == 1:
        # Second hint: show first, last, and some middle letters
        revealed = set([0, len(name) - 1])
        # Reveal ~30% of letters
        import random

        for i in range(1, len(name) - 1):
            if random.random() < 0.3:
                revealed.add(i)
        return "".join(c if i in revealed else "_" for i, c in enumerate(name))
    else:
        # Third hint: show most letters
        import random

        return "".join(c if random.random() < 0.7 else "_" for c in name)


@router.message(Command("catch", "c"))
async def cmd_catch(message: Message, session: AsyncSession, user: User) -> None:
    """Handle /catch command."""
    if not message.text:
        return

    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer(" Please specify the Pokemon name!\nUsage: /catch [name]")
        return

    pokemon_name = args[1].strip().lower()

    # Get active spawn for this chat
    chat_id = message.chat.id
    result = await session.execute(
        select(ActiveSpawn)
        .where(ActiveSpawn.chat_id == chat_id)
        .where(ActiveSpawn.caught_by.is_(None))
        .where(ActiveSpawn.expires_at > datetime.utcnow())
        .order_by(ActiveSpawn.spawned_at.desc())
        .limit(1)
    )
    spawn = result.scalar_one_or_none()

    if not spawn:
        await message.answer(" There's no wild Pokemon here right now!")
        return

    # Check if name matches (with fuzzy matching for typos)
    actual_name = spawn.species.name_lower
    similarity = fuzz.ratio(pokemon_name, actual_name)

    if similarity < 85:  # Require 85% similarity
        # Wrong name
        await message.answer(
            f" That's not the right Pokemon!\n"
            f"Use /hint if you need help identifying it."
        )
        return

    # Successful catch!
    import random
    import uuid

    # Generate random IVs (0-31)
    ivs = {
        "hp": random.randint(0, 31),
        "attack": random.randint(0, 31),
        "defense": random.randint(0, 31),
        "sp_attack": random.randint(0, 31),
        "sp_defense": random.randint(0, 31),
        "speed": random.randint(0, 31),
    }

    # Determine nature
    natures = [
        "hardy", "lonely", "brave", "adamant", "naughty",
        "bold", "docile", "relaxed", "impish", "lax",
        "timid", "hasty", "serious", "jolly", "naive",
        "modest", "mild", "quiet", "bashful", "rash",
        "calm", "gentle", "sassy", "careful", "quirky",
    ]
    nature = random.choice(natures)

    # Pick ability
    abilities = spawn.species.abilities or ["unknown"]
    ability = random.choice(abilities)

    # Determine gender
    gender = None
    if spawn.species.gender_ratio is not None:
        if spawn.species.gender_ratio == 0:
            gender = "male"
        elif spawn.species.gender_ratio == 100:
            gender = "female"
        else:
            gender = "female" if random.random() * 100 < spawn.species.gender_ratio else "male"

    # Create the Pokemon
    new_pokemon = Pokemon(
        id=uuid.uuid4(),
        owner_id=user.telegram_id,
        species_id=spawn.species_id,
        level=random.randint(1, 30),  # Random level 1-30
        iv_hp=ivs["hp"],
        iv_attack=ivs["attack"],
        iv_defense=ivs["defense"],
        iv_sp_attack=ivs["sp_attack"],
        iv_sp_defense=ivs["sp_defense"],
        iv_speed=ivs["speed"],
        nature=nature,
        ability=ability,
        is_shiny=spawn.is_shiny,
        gender=gender,
        original_trainer_id=user.telegram_id,
        caught_in_group_id=chat_id,
    )

    # Mark spawn as caught
    spawn.caught_by = user.telegram_id
    spawn.caught_at = datetime.utcnow()

    # Calculate rewards
    from telemon.config import settings

    reward = random.randint(settings.catch_reward_min, settings.catch_reward_max)

    # Bonus for rarity
    if spawn.species.is_legendary:
        reward *= 5
    elif spawn.species.is_mythical:
        reward *= 10
    elif spawn.species.rarity == "rare":
        reward *= 2

    # Bonus for shiny
    if spawn.is_shiny:
        reward *= 3

    user.balance += reward

    # Update pokedex
    pokedex_result = await session.execute(
        select(PokedexEntry)
        .where(PokedexEntry.user_id == user.telegram_id)
        .where(PokedexEntry.species_id == spawn.species_id)
    )
    pokedex_entry = pokedex_result.scalar_one_or_none()

    if pokedex_entry:
        pokedex_entry.caught = True
        pokedex_entry.times_caught += 1
        if spawn.is_shiny:
            pokedex_entry.caught_shiny = True
    else:
        pokedex_entry = PokedexEntry(
            user_id=user.telegram_id,
            species_id=spawn.species_id,
            seen=True,
            caught=True,
            caught_shiny=spawn.is_shiny,
            times_caught=1,
            first_caught_at=datetime.utcnow(),
        )
        session.add(pokedex_entry)

    # Update group stats
    group_result = await session.execute(
        select(Group).where(Group.chat_id == chat_id)
    )
    group = group_result.scalar_one_or_none()
    if group:
        group.total_catches += 1

    session.add(new_pokemon)
    await session.commit()

    # Build response message
    shiny_text = " **SHINY**" if spawn.is_shiny else ""
    iv_total = sum(ivs.values())
    iv_percent = round((iv_total / 186) * 100, 1)

    await message.answer(
        f"<b>Congratulations {user.display_name}!</b>\n\n"
        f"You caught a{shiny_text} <b>{spawn.species.name}</b>!\n\n"
        f" Level: {new_pokemon.level}\n"
        f" IVs: {iv_percent}%\n"
        f" Nature: {nature.capitalize()}\n"
        f" Ability: {ability}\n"
        f" Gender: {gender or 'Unknown'}\n\n"
        f" +{reward} Telecoins"
    )


@router.message(Command("hint"))
async def cmd_hint(message: Message, session: AsyncSession, user: User) -> None:
    """Handle /hint command with cooldown."""
    chat_id = message.chat.id
    user_id = user.telegram_id

    # Check cooldown
    cooldown_key = (chat_id, user_id)
    now = datetime.utcnow()
    
    if cooldown_key in _hint_cooldowns:
        last_hint = _hint_cooldowns[cooldown_key]
        time_since = (now - last_hint).total_seconds()
        if time_since < HINT_COOLDOWN_SECONDS:
            remaining = int(HINT_COOLDOWN_SECONDS - time_since)
            await message.answer(f"Please wait {remaining}s before using /hint again!")
            return

    # Get active spawn
    result = await session.execute(
        select(ActiveSpawn)
        .where(ActiveSpawn.chat_id == chat_id)
        .where(ActiveSpawn.caught_by.is_(None))
        .where(ActiveSpawn.expires_at > datetime.utcnow())
        .order_by(ActiveSpawn.spawned_at.desc())
        .limit(1)
    )
    spawn = result.scalar_one_or_none()

    if not spawn:
        await message.answer("There's no wild Pokemon here right now!")
        return

    # Update cooldown
    _hint_cooldowns[cooldown_key] = now

    # Generate hint
    hint = generate_hint(spawn.species.name, spawn.hints_used)
    spawn.hints_used += 1
    await session.commit()

    await message.answer(f"Hint: <code>{hint}</code>")
