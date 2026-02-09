"""Pokedex-related handlers for tracking Pokemon collection progress."""

import math
from datetime import datetime

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from telemon.database.models import PokedexEntry, Pokemon, PokemonSpecies, User
from telemon.logging import get_logger

router = Router(name="pokedex")
logger = get_logger(__name__)

# Constants
ENTRIES_PER_PAGE = 10
TOTAL_GEN1_POKEMON = 151


async def get_pokedex_stats(session: AsyncSession, user_id: int) -> dict:
    """Get pokedex completion statistics for a user."""
    # Count seen
    seen_result = await session.execute(
        select(func.count(PokedexEntry.species_id))
        .where(PokedexEntry.user_id == user_id)
        .where(PokedexEntry.seen == True)
    )
    seen_count = seen_result.scalar() or 0

    # Count caught
    caught_result = await session.execute(
        select(func.count(PokedexEntry.species_id))
        .where(PokedexEntry.user_id == user_id)
        .where(PokedexEntry.caught == True)
    )
    caught_count = caught_result.scalar() or 0

    # Count shiny caught
    shiny_result = await session.execute(
        select(func.count(PokedexEntry.species_id))
        .where(PokedexEntry.user_id == user_id)
        .where(PokedexEntry.caught_shiny == True)
    )
    shiny_count = shiny_result.scalar() or 0

    # Total catches (sum of times_caught)
    total_catches_result = await session.execute(
        select(func.sum(PokedexEntry.times_caught))
        .where(PokedexEntry.user_id == user_id)
    )
    total_catches = total_catches_result.scalar() or 0

    return {
        "seen": seen_count,
        "caught": caught_count,
        "shiny": shiny_count,
        "total_catches": total_catches,
        "total_pokemon": TOTAL_GEN1_POKEMON,
        "seen_percent": round((seen_count / TOTAL_GEN1_POKEMON) * 100, 1),
        "caught_percent": round((caught_count / TOTAL_GEN1_POKEMON) * 100, 1),
    }


async def get_pokedex_entries(
    session: AsyncSession,
    user_id: int,
    page: int = 1,
    filter_type: str = "all",  # all, caught, missing, shiny, seen
) -> tuple[list[dict], int]:
    """Get pokedex entries with filters."""
    # Get all species
    species_result = await session.execute(
        select(PokemonSpecies).order_by(PokemonSpecies.national_dex)
    )
    all_species = list(species_result.scalars().all())

    # Get user's pokedex entries
    entries_result = await session.execute(
        select(PokedexEntry).where(PokedexEntry.user_id == user_id)
    )
    user_entries = {e.species_id: e for e in entries_result.scalars().all()}

    # Build filtered list
    filtered_entries = []
    for species in all_species:
        entry = user_entries.get(species.national_dex)
        seen = entry.seen if entry else False
        caught = entry.caught if entry else False
        caught_shiny = entry.caught_shiny if entry else False
        times_caught = entry.times_caught if entry else 0

        entry_data = {
            "dex_num": species.national_dex,
            "name": species.name,
            "type1": species.type1,
            "type2": species.type2,
            "seen": seen,
            "caught": caught,
            "caught_shiny": caught_shiny,
            "times_caught": times_caught,
        }

        # Apply filter
        if filter_type == "all":
            filtered_entries.append(entry_data)
        elif filter_type == "caught" and caught:
            filtered_entries.append(entry_data)
        elif filter_type == "missing" and not caught:
            filtered_entries.append(entry_data)
        elif filter_type == "shiny" and caught_shiny:
            filtered_entries.append(entry_data)
        elif filter_type == "seen" and seen and not caught:
            filtered_entries.append(entry_data)

    # Paginate
    total_count = len(filtered_entries)
    start_idx = (page - 1) * ENTRIES_PER_PAGE
    end_idx = start_idx + ENTRIES_PER_PAGE
    page_entries = filtered_entries[start_idx:end_idx]

    return page_entries, total_count


async def get_species_by_name_or_number(
    session: AsyncSession, query: str
) -> PokemonSpecies | None:
    """Find a Pokemon species by name or dex number."""
    # Try as number first
    if query.isdigit():
        result = await session.execute(
            select(PokemonSpecies)
            .where(PokemonSpecies.national_dex == int(query))
        )
        return result.scalar_one_or_none()

    # Try as name
    result = await session.execute(
        select(PokemonSpecies)
        .where(PokemonSpecies.name.ilike(query))
    )
    species = result.scalar_one_or_none()
    if species:
        return species

    # Try partial match
    result = await session.execute(
        select(PokemonSpecies)
        .where(PokemonSpecies.name.ilike(f"%{query}%"))
        .limit(1)
    )
    return result.scalar_one_or_none()


def build_pokedex_keyboard(
    page: int, total_pages: int, filter_type: str = "all"
) -> InlineKeyboardBuilder:
    """Build pagination keyboard for pokedex."""
    builder = InlineKeyboardBuilder()

    # Pagination row
    if total_pages > 1:
        nav_buttons = []
        if page > 1:
            nav_buttons.append(("◀️", f"dex:page:{page - 1}:{filter_type}"))
        nav_buttons.append((f"{page}/{total_pages}", "dex:noop"))
        if page < total_pages:
            nav_buttons.append(("▶️", f"dex:page:{page + 1}:{filter_type}"))

        for text, callback_data in nav_buttons:
            builder.button(text=text, callback_data=callback_data)

    # Filter row
    filter_buttons = [
        ("📖 All", "dex:filter:all:1"),
        ("✅ Caught", "dex:filter:caught:1"),
        ("❌ Missing", "dex:filter:missing:1"),
        ("✨ Shiny", "dex:filter:shiny:1"),
    ]

    for text, callback_data in filter_buttons:
        # Highlight active filter
        if filter_type in callback_data:
            text = f"[{text}]"
        builder.button(text=text, callback_data=callback_data)

    builder.adjust(3, 4)  # 3 nav buttons, 4 filter buttons

    return builder


def format_dex_entry_line(entry: dict, show_details: bool = False) -> str:
    """Format a single pokedex entry for list display."""
    dex_num = entry["dex_num"]
    name = entry["name"]
    caught = entry["caught"]
    seen = entry["seen"]
    shiny = entry["caught_shiny"]

    # Status icon
    if caught:
        if shiny:
            status = "✨"
        else:
            status = "✅"
    elif seen:
        status = "👁️"
    else:
        status = "❓"

    # Type display
    types = entry["type1"].title()
    if entry["type2"]:
        types += f"/{entry['type2'].title()}"

    if show_details and caught:
        return f"{status} #{dex_num:03d} <b>{name}</b> [{types}] (x{entry['times_caught']})"
    elif caught or seen:
        return f"{status} #{dex_num:03d} <b>{name}</b> [{types}]"
    else:
        return f"{status} #{dex_num:03d} ???"


def generate_progress_bar(percent: float, width: int = 10) -> str:
    """Generate a text-based progress bar."""
    filled = int(percent / 100 * width)
    empty = width - filled
    return "█" * filled + "░" * empty


@router.message(Command("pokedex", "dex"))
async def cmd_pokedex(message: Message, session: AsyncSession, user: User) -> None:
    """Handle /pokedex command and subcommands."""
    text = message.text or ""
    args = text.split()

    if len(args) < 2:
        # Show overview
        await show_pokedex_overview(message, session, user)
        return

    subcommand = args[1].lower()

    if subcommand in ["list", "all"]:
        await show_pokedex_list(message, session, user, filter_type="all")
    elif subcommand in ["caught", "owned"]:
        await show_pokedex_list(message, session, user, filter_type="caught")
    elif subcommand in ["missing", "uncaught", "needed"]:
        await show_pokedex_list(message, session, user, filter_type="missing")
    elif subcommand in ["shiny", "shinies"]:
        await show_pokedex_list(message, session, user, filter_type="shiny")
    elif subcommand in ["seen"]:
        await show_pokedex_list(message, session, user, filter_type="seen")
    elif subcommand in ["search", "find"]:
        if len(args) > 2:
            await pokedex_search(message, session, user, " ".join(args[2:]))
        else:
            await message.answer("Usage: /pokedex search [name or number]")
    elif subcommand == "help":
        await pokedex_help(message)
    else:
        # Try to look up by name or number
        await pokedex_search(message, session, user, subcommand)


async def show_pokedex_overview(
    message: Message, session: AsyncSession, user: User
) -> None:
    """Show pokedex completion overview."""
    stats = await get_pokedex_stats(session, user.telegram_id)

    caught_bar = generate_progress_bar(stats["caught_percent"])
    seen_bar = generate_progress_bar(stats["seen_percent"])

    # Recent catches
    recent_result = await session.execute(
        select(PokedexEntry)
        .where(PokedexEntry.user_id == user.telegram_id)
        .where(PokedexEntry.caught == True)
        .order_by(PokedexEntry.first_caught_at.desc())
        .limit(5)
    )
    recent_entries = list(recent_result.scalars().all())

    recent_lines = []
    for entry in recent_entries:
        shiny = "✨" if entry.caught_shiny else ""
        recent_lines.append(f"  #{entry.species_id:03d} {entry.species.name}{shiny}")

    recent_text = "\n".join(recent_lines) if recent_lines else "  <i>None yet!</i>"

    await message.answer(
        f"📕 <b>{user.display_name}'s Pokédex</b>\n\n"
        f"<b>Caught:</b> {stats['caught']}/{stats['total_pokemon']} ({stats['caught_percent']}%)\n"
        f"[{caught_bar}]\n\n"
        f"<b>Seen:</b> {stats['seen']}/{stats['total_pokemon']} ({stats['seen_percent']}%)\n"
        f"[{seen_bar}]\n\n"
        f"✨ <b>Shinies:</b> {stats['shiny']}\n"
        f"🎯 <b>Total Catches:</b> {stats['total_catches']}\n\n"
        f"<b>Recent Catches:</b>\n{recent_text}\n\n"
        f"<b>Commands:</b>\n"
        f"/pokedex list - Browse all entries\n"
        f"/pokedex caught - View caught Pokemon\n"
        f"/pokedex missing - View uncaught Pokemon\n"
        f"/pokedex [name/#] - Look up Pokemon"
    )


async def show_pokedex_list(
    message: Message,
    session: AsyncSession,
    user: User,
    filter_type: str = "all",
    page: int = 1,
) -> None:
    """Show paginated pokedex list."""
    entries, total_count = await get_pokedex_entries(
        session, user.telegram_id, page=page, filter_type=filter_type
    )

    if not entries:
        filter_names = {
            "all": "entries",
            "caught": "caught Pokemon",
            "missing": "missing Pokemon",
            "shiny": "shiny Pokemon",
            "seen": "seen (but uncaught) Pokemon",
        }
        await message.answer(
            f"📕 <b>Pokédex</b>\n\n"
            f"No {filter_names.get(filter_type, 'entries')} found!"
        )
        return

    total_pages = math.ceil(total_count / ENTRIES_PER_PAGE)

    # Format header
    filter_titles = {
        "all": "All Pokemon",
        "caught": "Caught Pokemon",
        "missing": "Missing Pokemon",
        "shiny": "Shiny Pokemon",
        "seen": "Seen (Uncaught)",
    }

    lines = [
        f"📕 <b>Pokédex - {filter_titles.get(filter_type, 'All')}</b>",
        f"<i>Showing {len(entries)} of {total_count}</i>\n",
    ]

    for entry in entries:
        lines.append(format_dex_entry_line(entry, show_details=True))

    lines.append("\n<b>Legend:</b> ✅ Caught | ✨ Shiny | 👁️ Seen | ❓ Unknown")

    keyboard = build_pokedex_keyboard(page, total_pages, filter_type)

    await message.answer("\n".join(lines), reply_markup=keyboard.as_markup())


async def pokedex_search(
    message: Message, session: AsyncSession, user: User, query: str
) -> None:
    """Search for and display a specific Pokemon entry."""
    species = await get_species_by_name_or_number(session, query)

    if not species:
        await message.answer(
            f"❌ Pokemon '{query}' not found.\n"
            "Try using the National Dex number or exact name."
        )
        return

    # Get user's entry for this species
    entry_result = await session.execute(
        select(PokedexEntry)
        .where(PokedexEntry.user_id == user.telegram_id)
        .where(PokedexEntry.species_id == species.national_dex)
    )
    entry = entry_result.scalar_one_or_none()

    # Get user's Pokemon of this species
    pokemon_result = await session.execute(
        select(Pokemon)
        .where(Pokemon.owner_id == user.telegram_id)
        .where(Pokemon.species_id == species.national_dex)
        .order_by(Pokemon.level.desc())
        .limit(5)
    )
    user_pokemon = list(pokemon_result.scalars().all())

    # Build response
    seen = entry.seen if entry else False
    caught = entry.caught if entry else False
    caught_shiny = entry.caught_shiny if entry else False
    times_caught = entry.times_caught if entry else 0
    first_caught = entry.first_caught_at if entry else None

    # Status
    if caught:
        status = "✅ Caught"
        if caught_shiny:
            status += " ✨ (Shiny obtained!)"
    elif seen:
        status = "👁️ Seen"
    else:
        status = "❓ Not encountered"

    # Types
    types = species.type1.title()
    if species.type2:
        types += f" / {species.type2.title()}"

    # Base stats
    stats_line = (
        f"HP: {species.base_hp} | ATK: {species.base_attack} | DEF: {species.base_defense}\n"
        f"SpA: {species.base_sp_attack} | SpD: {species.base_sp_defense} | SPE: {species.base_speed}"
    )

    # Rarity
    rarity = species.rarity.title() if species.rarity else "Common"
    if species.is_legendary:
        rarity = "🌟 Legendary"
    elif species.is_mythical:
        rarity = "💫 Mythical"

    # User's Pokemon of this species
    owned_lines = []
    if user_pokemon:
        for poke in user_pokemon:
            shiny = "✨" if poke.is_shiny else ""
            owned_lines.append(
                f"  Lv.{poke.level} | IV: {poke.iv_percentage:.1f}% | {poke.nature.title()}{shiny}"
            )
        owned_text = "\n".join(owned_lines)
    else:
        owned_text = "  <i>None</i>"

    # First caught info
    first_caught_text = ""
    if first_caught:
        first_caught_text = f"\n<b>First Caught:</b> {first_caught.strftime('%Y-%m-%d')}"

    await message.answer(
        f"📕 <b>Pokédex Entry #{species.national_dex:03d}</b>\n\n"
        f"<b>{species.name}</b>\n"
        f"Type: {types}\n"
        f"Rarity: {rarity}\n\n"
        f"<b>Status:</b> {status}\n"
        f"<b>Times Caught:</b> {times_caught}{first_caught_text}\n\n"
        f"<b>Base Stats:</b>\n{stats_line}\n\n"
        f"<b>Your {species.name}:</b>\n{owned_text}"
    )


async def pokedex_help(message: Message) -> None:
    """Show pokedex help."""
    await message.answer(
        "📕 <b>Pokédex Commands</b>\n\n"
        "<b>Overview:</b>\n"
        "/pokedex - Show completion overview\n\n"
        "<b>Browse:</b>\n"
        "/pokedex list - All entries\n"
        "/pokedex caught - Caught Pokemon\n"
        "/pokedex missing - Uncaught Pokemon\n"
        "/pokedex shiny - Shinies obtained\n"
        "/pokedex seen - Seen but uncaught\n\n"
        "<b>Search:</b>\n"
        "/pokedex [name] - Look up by name\n"
        "/pokedex [number] - Look up by Dex #\n"
        "/pokedex search [query]\n\n"
        "<b>Legend:</b>\n"
        "✅ Caught | ✨ Shiny | 👁️ Seen | ❓ Unknown"
    )


@router.callback_query(F.data.startswith("dex:"))
async def handle_pokedex_callback(
    callback: CallbackQuery, session: AsyncSession, user: User
) -> None:
    """Handle pokedex pagination and filter callbacks."""
    data = callback.data.split(":")

    if len(data) < 2:
        await callback.answer("Invalid callback")
        return

    action = data[1]

    if action == "noop":
        await callback.answer()
        return

    if action == "page":
        page = int(data[2]) if len(data) > 2 else 1
        filter_type = data[3] if len(data) > 3 else "all"

        entries, total_count = await get_pokedex_entries(
            session, user.telegram_id, page=page, filter_type=filter_type
        )

        if not entries:
            await callback.answer("No entries on this page")
            return

        total_pages = math.ceil(total_count / ENTRIES_PER_PAGE)

        filter_titles = {
            "all": "All Pokemon",
            "caught": "Caught Pokemon",
            "missing": "Missing Pokemon",
            "shiny": "Shiny Pokemon",
            "seen": "Seen (Uncaught)",
        }

        lines = [
            f"📕 <b>Pokédex - {filter_titles.get(filter_type, 'All')}</b>",
            f"<i>Showing {len(entries)} of {total_count}</i>\n",
        ]

        for entry in entries:
            lines.append(format_dex_entry_line(entry, show_details=True))

        lines.append("\n<b>Legend:</b> ✅ Caught | ✨ Shiny | 👁️ Seen | ❓ Unknown")

        keyboard = build_pokedex_keyboard(page, total_pages, filter_type)

        await callback.message.edit_text(
            "\n".join(lines), reply_markup=keyboard.as_markup()
        )
        await callback.answer()

    elif action == "filter":
        filter_type = data[2] if len(data) > 2 else "all"
        page = int(data[3]) if len(data) > 3 else 1

        entries, total_count = await get_pokedex_entries(
            session, user.telegram_id, page=page, filter_type=filter_type
        )

        if not entries:
            filter_names = {
                "all": "entries",
                "caught": "caught Pokemon",
                "missing": "missing Pokemon",
                "shiny": "shiny Pokemon",
                "seen": "seen (but uncaught) Pokemon",
            }
            await callback.answer(f"No {filter_names.get(filter_type, 'entries')} found!")
            return

        total_pages = math.ceil(total_count / ENTRIES_PER_PAGE)

        filter_titles = {
            "all": "All Pokemon",
            "caught": "Caught Pokemon",
            "missing": "Missing Pokemon",
            "shiny": "Shiny Pokemon",
            "seen": "Seen (Uncaught)",
        }

        lines = [
            f"📕 <b>Pokédex - {filter_titles.get(filter_type, 'All')}</b>",
            f"<i>Showing {len(entries)} of {total_count}</i>\n",
        ]

        for entry in entries:
            lines.append(format_dex_entry_line(entry, show_details=True))

        lines.append("\n<b>Legend:</b> ✅ Caught | ✨ Shiny | 👁️ Seen | ❓ Unknown")

        keyboard = build_pokedex_keyboard(page, total_pages, filter_type)

        await callback.message.edit_text(
            "\n".join(lines), reply_markup=keyboard.as_markup()
        )
        await callback.answer(f"Showing {filter_titles.get(filter_type, 'all')}")
