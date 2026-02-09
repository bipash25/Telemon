"""Start and welcome handlers with starter Pokemon selection."""

import random
import uuid
from datetime import datetime

from aiogram import Bot, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from telemon.database.models import Pokemon, PokemonSpecies, User
from telemon.logging import get_logger

router = Router(name="start")
logger = get_logger(__name__)

# Gen 1 starters
STARTER_POKEMON = {
    "bulbasaur": 1,
    "charmander": 4,
    "squirtle": 7,
    "pikachu": 25,
}

WELCOME_NEW_USER = """
<b>Welcome to Telemon!</b>

A Pokemon-style game right here on Telegram!

<b>Choose your starter Pokemon to begin your journey!</b>
"""

WELCOME_MESSAGE = """
<b>Welcome to Telemon!</b>

A Pokemon-style game right here on Telegram!

<b>What can you do?</b>
- Catch wild Pokemon that spawn in group chats
- Build your collection and train them
- Battle other trainers in PvP duels
- Trade Pokemon and items with friends
- Buy and sell on the global market

<b>Quick Start:</b>
1. Add me to a group chat
2. Chat with friends - Pokemon will spawn!
3. Use /catch &lt;name&gt; to catch them
4. Use /pokemon to see your collection

<b>Need help?</b> Use /help to see all commands.

<i>Good luck, Trainer!</i>
"""

RETURNING_MESSAGE = """
<b>Welcome back, {name}!</b>

Pokemon caught: <b>{pokemon_count}</b>
Balance: <b>{balance}</b> Telecoins

Use /pokemon to manage your collection or /help for commands.
"""


def get_starter_keyboard() -> InlineKeyboardMarkup:
    """Create inline keyboard for starter selection."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Bulbasaur", callback_data="starter:bulbasaur"),
                InlineKeyboardButton(text="Charmander", callback_data="starter:charmander"),
            ],
            [
                InlineKeyboardButton(text="Squirtle", callback_data="starter:squirtle"),
                InlineKeyboardButton(text="Pikachu", callback_data="starter:pikachu"),
            ],
        ]
    )


@router.message(CommandStart())
async def cmd_start(message: Message, session: AsyncSession, user: User) -> None:
    """Handle /start command."""
    # Check if user has any Pokemon (not just if they're new)
    result = await session.execute(
        select(func.count(Pokemon.id)).where(Pokemon.owner_id == user.telegram_id)
    )
    pokemon_count = result.scalar() or 0

    if pokemon_count == 0:
        # New user without Pokemon - show starter selection
        await message.answer(
            WELCOME_NEW_USER,
            reply_markup=get_starter_keyboard(),
        )
    else:
        # Returning user with Pokemon
        await message.answer(
            RETURNING_MESSAGE.format(
                name=user.display_name,
                pokemon_count=pokemon_count,
                balance=user.balance,
            )
        )


@router.callback_query(F.data.startswith("starter:"))
async def callback_starter_selection(
    callback: CallbackQuery,
    session: AsyncSession,
    user: User,
    bot: Bot,
) -> None:
    """Handle starter Pokemon selection."""
    if not callback.data:
        return

    starter_name = callback.data.split(":")[1]
    if starter_name not in STARTER_POKEMON:
        await callback.answer("Invalid starter!", show_alert=True)
        return

    # Check if user already has Pokemon
    result = await session.execute(
        select(func.count(Pokemon.id)).where(Pokemon.owner_id == user.telegram_id)
    )
    pokemon_count = result.scalar() or 0

    if pokemon_count > 0:
        await callback.answer("You already have Pokemon!", show_alert=True)
        return

    # Get the species
    species_id = STARTER_POKEMON[starter_name]
    result = await session.execute(
        select(PokemonSpecies).where(PokemonSpecies.national_dex == species_id)
    )
    species = result.scalar_one_or_none()

    if not species:
        await callback.answer("Species not found!", show_alert=True)
        return

    # Generate starter stats (slightly better IVs for starters)
    ivs = {
        "hp": random.randint(10, 31),
        "attack": random.randint(10, 31),
        "defense": random.randint(10, 31),
        "sp_attack": random.randint(10, 31),
        "sp_defense": random.randint(10, 31),
        "speed": random.randint(10, 31),
    }

    natures = [
        "hardy", "lonely", "brave", "adamant", "naughty",
        "bold", "docile", "relaxed", "impish", "lax",
        "timid", "hasty", "serious", "jolly", "naive",
        "modest", "mild", "quiet", "bashful", "rash",
        "calm", "gentle", "sassy", "careful", "quirky",
    ]
    nature = random.choice(natures)

    abilities = species.abilities or ["unknown"]
    ability = random.choice(abilities)

    gender = None
    if species.gender_ratio is not None:
        if species.gender_ratio == 0:
            gender = "male"
        elif species.gender_ratio == 100:
            gender = "female"
        else:
            gender = "female" if random.random() * 100 < species.gender_ratio else "male"

    # Create the starter Pokemon at level 5
    starter = Pokemon(
        id=uuid.uuid4(),
        owner_id=user.telegram_id,
        species_id=species_id,
        level=5,
        iv_hp=ivs["hp"],
        iv_attack=ivs["attack"],
        iv_defense=ivs["defense"],
        iv_sp_attack=ivs["sp_attack"],
        iv_sp_defense=ivs["sp_defense"],
        iv_speed=ivs["speed"],
        nature=nature,
        ability=ability,
        is_shiny=False,
        gender=gender,
        original_trainer_id=user.telegram_id,
        is_favorite=True,  # Starter is automatically favorited
    )

    session.add(starter)
    user.selected_pokemon_id = str(starter.id)  # Convert UUID to string
    await session.commit()

    iv_total = sum(ivs.values())
    iv_percent = round((iv_total / 186) * 100, 1)

    # Edit the original message
    await callback.message.edit_text(
        f"<b>Congratulations, {user.display_name}!</b>\n\n"
        f"You chose <b>{species.name}</b> as your starter Pokemon!\n\n"
        f"Level: 5\n"
        f"IVs: {iv_percent}%\n"
        f"Nature: {nature.capitalize()}\n"
        f"Ability: {ability}\n"
        f"Gender: {gender or 'Unknown'}\n\n"
        f"<i>Your journey begins now! Add me to a group chat to start catching more Pokemon!</i>\n\n"
        f"Use /help to see all available commands."
    )

    await callback.answer(f"You chose {species.name}!")

    logger.info(
        "User selected starter",
        user_id=user.telegram_id,
        starter=species.name,
    )


@router.message(Command("ping"))
async def cmd_ping(message: Message) -> None:
    """Simple ping command to test bot responsiveness."""
    await message.answer("Pong!")
