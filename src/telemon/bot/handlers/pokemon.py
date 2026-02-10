"""Pokemon collection handlers."""

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from telemon.core.evolution import check_evolution, evolve_pokemon, get_possible_evolutions
from telemon.database.models import Pokemon, PokemonSpecies, User
from telemon.logging import get_logger

router = Router(name="pokemon")
logger = get_logger(__name__)

POKEMON_PER_PAGE = 15


def parse_pokemon_args(text: str) -> dict:
    """Parse filter and sort arguments from command.
    
    Supports both formats:
      /pokemon --shiny --type fire --order iv
      /pokemon shiny type:fire sort:iv gen:3 name:char
    """
    args = {
        "shiny": False,
        "legendary": False,
        "mythical": False,
        "favorites": False,
        "name": None,
        "type": None,
        "gen": None,
        "order": "recent",
        "page": 1,
    }

    if not text:
        return args

    parts = text.split()
    i = 0
    while i < len(parts):
        part = parts[i].lower()

        # Flag-style arguments
        if part in ("--shiny", "shiny"):
            args["shiny"] = True
        elif part in ("--legendary", "legendary", "leg"):
            args["legendary"] = True
        elif part in ("--mythical", "mythical", "myth"):
            args["mythical"] = True
        elif part in ("--favorites", "--fav", "favorites", "fav"):
            args["favorites"] = True

        # Key:value style arguments
        elif ":" in part:
            key, _, value = part.partition(":")
            if key in ("type", "t") and value:
                args["type"] = value
            elif key in ("gen", "g", "generation") and value.isdigit():
                args["gen"] = int(value)
            elif key in ("name", "n") and value:
                args["name"] = value
            elif key in ("sort", "order", "o") and value:
                args["order"] = value
            elif key in ("page", "p") and value.isdigit():
                args["page"] = int(value)

        # Legacy --key value style
        elif part == "--name" and i + 1 < len(parts):
            i += 1
            args["name"] = parts[i].lower()
        elif part == "--type" and i + 1 < len(parts):
            i += 1
            args["type"] = parts[i].lower()
        elif part == "--order" and i + 1 < len(parts):
            i += 1
            args["order"] = parts[i].lower()
        elif part == "--gen" and i + 1 < len(parts):
            i += 1
            if parts[i].isdigit():
                args["gen"] = int(parts[i])

        # Page number as plain digit
        elif part.isdigit():
            args["page"] = int(part)

        i += 1

    return args


async def get_user_pokemon_by_index(
    session: AsyncSession, user_id: int, index: int
) -> Pokemon | None:
    """Get a user's Pokemon by 1-based index (ordered by catch date desc)."""
    result = await session.execute(
        select(Pokemon)
        .where(Pokemon.owner_id == user_id)
        .order_by(Pokemon.caught_at.desc())
        .offset(index - 1)
        .limit(1)
    )
    return result.scalar_one_or_none()


async def resolve_pokemon(
    session: AsyncSession, user: User, arg: str | None
) -> Pokemon | None:
    """Resolve a Pokemon from argument (index number or 'latest') or selected Pokemon."""
    if arg:
        if arg.isdigit():
            return await get_user_pokemon_by_index(session, user.telegram_id, int(arg))
        elif arg == "latest":
            return await get_user_pokemon_by_index(session, user.telegram_id, 1)
    
    # Fall back to selected Pokemon
    if user.selected_pokemon_id:
        result = await session.execute(
            select(Pokemon)
            .where(Pokemon.id == user.selected_pokemon_id)
            .where(Pokemon.owner_id == user.telegram_id)
        )
        return result.scalar_one_or_none()
    
    return None


@router.message(Command("pokemon", "p"))
async def cmd_pokemon(message: Message, session: AsyncSession, user: User) -> None:
    """Handle /pokemon command to list user's Pokemon."""
    # Parse arguments
    text = message.text or ""
    args = parse_pokemon_args(text.split(maxsplit=1)[1] if " " in text else "")

    # Build query
    query = (
        select(Pokemon)
        .where(Pokemon.owner_id == user.telegram_id)
        .join(PokemonSpecies, Pokemon.species_id == PokemonSpecies.national_dex)
    )

    # Apply filters
    if args["shiny"]:
        query = query.where(Pokemon.is_shiny == True)
    if args["legendary"]:
        query = query.where(PokemonSpecies.is_legendary == True)
    if args["mythical"]:
        query = query.where(PokemonSpecies.is_mythical == True)
    if args["favorites"]:
        query = query.where(Pokemon.is_favorite == True)
    if args["name"]:
        query = query.where(PokemonSpecies.name_lower.contains(args["name"]))
    if args["type"]:
        query = query.where(
            (PokemonSpecies.type1 == args["type"]) | (PokemonSpecies.type2 == args["type"])
        )
    if args["gen"]:
        query = query.where(PokemonSpecies.generation == args["gen"])

    # Apply sorting
    order = args["order"]
    if order == "iv":
        query = query.order_by(
            (
                Pokemon.iv_hp
                + Pokemon.iv_attack
                + Pokemon.iv_defense
                + Pokemon.iv_sp_attack
                + Pokemon.iv_sp_defense
                + Pokemon.iv_speed
            ).desc()
        )
    elif order == "level":
        query = query.order_by(Pokemon.level.desc())
    elif order == "dex":
        query = query.order_by(PokemonSpecies.national_dex.asc())
    elif order == "name":
        query = query.order_by(PokemonSpecies.name.asc())
    else:  # recent (default)
        query = query.order_by(Pokemon.caught_at.desc())

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await session.execute(count_query)
    total_count = total_result.scalar() or 0

    if total_count == 0:
        has_filter = args["shiny"] or args["legendary"] or args["mythical"] or args["favorites"] or args["name"] or args["type"] or args["gen"]
        if has_filter:
            await message.answer("No Pokemon match your filters.")
        else:
            await message.answer(
                "You don't have any Pokemon yet!\n"
                "Catch some in group chats with /catch"
            )
        return

    # Paginate
    page = args["page"]
    total_pages = (total_count + POKEMON_PER_PAGE - 1) // POKEMON_PER_PAGE
    page = max(1, min(page, total_pages))
    offset = (page - 1) * POKEMON_PER_PAGE
    query = query.offset(offset).limit(POKEMON_PER_PAGE)

    result = await session.execute(query)
    pokemon_list = result.scalars().all()

    # Build active filter description
    filter_parts = []
    if args["shiny"]:
        filter_parts.append("shiny")
    if args["legendary"]:
        filter_parts.append("legendary")
    if args["mythical"]:
        filter_parts.append("mythical")
    if args["favorites"]:
        filter_parts.append("favorites")
    if args["type"]:
        filter_parts.append(f"type:{args['type']}")
    if args["gen"]:
        filter_parts.append(f"gen:{args['gen']}")
    if args["name"]:
        filter_parts.append(f"name:{args['name']}")
    
    filter_text = f" [{', '.join(filter_parts)}]" if filter_parts else ""
    sort_text = f" sorted by {order}" if order != "recent" else ""

    # Build response
    lines = [f"<b>Your Pokemon</b> ({total_count} total){filter_text}{sort_text}\n"]

    for i, poke in enumerate(pokemon_list):
        idx = offset + i + 1
        shiny = "✨ " if poke.is_shiny else ""
        fav = "❤️ " if poke.is_favorite else ""
        
        # Show species name + nickname if nicknamed
        if poke.nickname:
            name = f"{poke.nickname} ({poke.species.name})"
        else:
            name = poke.species.name
        
        iv_pct = poke.iv_percentage
        
        # Selected indicator
        selected = " ◀️" if str(poke.id) == user.selected_pokemon_id else ""

        lines.append(
            f"{idx}. {shiny}{fav}<b>{name}</b> "
            f"Lv.{poke.level} | {iv_pct}% IV{selected}"
        )

    # Pagination info
    if total_pages > 1:
        lines.append(f"\nPage {page}/{total_pages}")
        lines.append(f"<i>Use /pokemon {page + 1} for next page</i>" if page < total_pages else "")

    # Build pagination keyboard
    builder = InlineKeyboardBuilder()
    if page > 1:
        builder.button(text="◀️ Prev", callback_data=f"pokemon:page:{page - 1}")
    if page < total_pages:
        builder.button(text="Next ▶️", callback_data=f"pokemon:page:{page + 1}")
    builder.adjust(2)

    await message.answer("\n".join(lines), reply_markup=builder.as_markup() if total_pages > 1 else None)


@router.message(Command("info", "i"))
async def cmd_info(message: Message, session: AsyncSession, user: User) -> None:
    """Handle /info command to show Pokemon details."""
    text = message.text or ""
    args = text.split()
    
    arg = args[1] if len(args) >= 2 else None
    poke = await resolve_pokemon(session, user, arg)

    if not poke:
        await message.answer(
            "Pokemon not found!\n"
            "Usage: /info [number] or select one with /select"
        )
        return

    # Build detailed info
    shiny = " ✨ SHINY" if poke.is_shiny else ""
    fav = " ❤️" if poke.is_favorite else ""

    type_text = poke.species.type1.capitalize()
    if poke.species.type2:
        type_text += f" / {poke.species.type2.capitalize()}"

    gender_text = ""
    if poke.gender == "male":
        gender_text = " ♂"
    elif poke.gender == "female":
        gender_text = " ♀"

    # IV quality
    iv_pct = poke.iv_percentage
    if iv_pct >= 90:
        iv_rating = "⭐ Amazing"
    elif iv_pct >= 75:
        iv_rating = "Great"
    elif iv_pct >= 50:
        iv_rating = "Good"
    elif iv_pct >= 25:
        iv_rating = "Average"
    else:
        iv_rating = "Poor"

    nickname_line = f'\nNickname: "{poke.nickname}"' if poke.nickname else ""

    info = f"""\
<b>{poke.display_name}</b>{shiny}{fav}{gender_text}
{poke.species.name} #{poke.species.national_dex} | Gen {poke.species.generation}{nickname_line}

<b>Type:</b> {type_text}
<b>Level:</b> {poke.level}
<b>Nature:</b> {poke.nature.capitalize()}
<b>Ability:</b> {poke.ability or "Unknown"}

<b>IVs</b> ({iv_pct}% - {iv_rating})
HP: {poke.iv_hp} | Atk: {poke.iv_attack} | Def: {poke.iv_defense}
SpA: {poke.iv_sp_attack} | SpD: {poke.iv_sp_defense} | Spe: {poke.iv_speed}

<b>Held Item:</b> {poke.held_item or 'None'}
<b>Friendship:</b> {poke.friendship}/255

<i>Caught {poke.caught_at.strftime('%Y-%m-%d')}</i>"""

    await message.answer(info)


@router.message(Command("select", "sel"))
async def cmd_select(message: Message, session: AsyncSession, user: User) -> None:
    """Handle /select command to set active Pokemon."""
    text = message.text or ""
    args = text.split()

    if len(args) < 2 or not args[1].isdigit():
        await message.answer("Usage: /select [number]\nExample: /select 1")
        return

    poke = await get_user_pokemon_by_index(session, user.telegram_id, int(args[1]))

    if not poke:
        await message.answer("Pokemon not found! Check your list with /pokemon")
        return

    user.selected_pokemon_id = str(poke.id)
    await session.commit()

    shiny = " ✨" if poke.is_shiny else ""
    await message.answer(
        f"Selected <b>{poke.display_name}</b>{shiny} (Lv.{poke.level}) as your active Pokemon!"
    )


@router.message(Command("nickname", "nick"))
async def cmd_nickname(message: Message, session: AsyncSession, user: User) -> None:
    """Handle /nickname command to rename selected Pokemon."""
    text = message.text or ""
    args = text.split(maxsplit=1)

    if len(args) < 2:
        await message.answer(
            "<b>Usage:</b>\n"
            "/nickname [new name] - Rename selected Pokemon\n"
            "/nickname clear - Remove nickname\n\n"
            "Select a Pokemon first with /select [number]"
        )
        return

    new_name = args[1].strip()

    # Get selected Pokemon
    poke = await resolve_pokemon(session, user, None)
    if not poke:
        await message.answer("No Pokemon selected! Use /select [number] first.")
        return

    if new_name.lower() == "clear":
        old_name = poke.nickname or poke.species.name
        poke.nickname = None
        await session.commit()
        await message.answer(f"Cleared nickname for <b>{poke.species.name}</b>!")
        return

    # Validate nickname
    if len(new_name) > 30:
        await message.answer("Nickname is too long! Max 30 characters.")
        return

    if len(new_name) < 1:
        await message.answer("Nickname cannot be empty!")
        return

    old_name = poke.display_name
    poke.nickname = new_name[:30]
    await session.commit()

    await message.answer(
        f"Renamed <b>{old_name}</b> to <b>{new_name}</b>! ({poke.species.name})"
    )


@router.message(Command("favorite", "fav"))
async def cmd_favorite(message: Message, session: AsyncSession, user: User) -> None:
    """Handle /favorite command to toggle favorite status."""
    text = message.text or ""
    args = text.split()

    arg = args[1] if len(args) >= 2 else None
    poke = await resolve_pokemon(session, user, arg)

    if not poke:
        await message.answer(
            "Pokemon not found!\n"
            "Usage: /fav [number] or select one with /select first"
        )
        return

    poke.is_favorite = not poke.is_favorite
    await session.commit()

    if poke.is_favorite:
        await message.answer(f"❤️ <b>{poke.display_name}</b> is now a favorite!")
    else:
        await message.answer(f"<b>{poke.display_name}</b> removed from favorites.")


@router.message(Command("release"))
async def cmd_release(message: Message, session: AsyncSession, user: User) -> None:
    """Handle /release command to release a Pokemon."""
    text = message.text or ""
    args = text.split()

    arg = args[1] if len(args) >= 2 else None
    poke = await resolve_pokemon(session, user, arg)

    if not poke:
        await message.answer(
            "Pokemon not found!\n"
            "Usage: /release [number]"
        )
        return

    if not poke.is_releasable:
        if poke.is_favorite:
            await message.answer(
                "This Pokemon is a favorite! "
                "Remove from favorites first with /fav"
            )
        else:
            await message.answer("This Pokemon cannot be released right now.")
        return

    # Build confirmation keyboard
    builder = InlineKeyboardBuilder()
    builder.button(text="Yes, release", callback_data=f"release:confirm:{poke.id}")
    builder.button(text="Cancel", callback_data="release:cancel")
    builder.adjust(2)

    await message.answer(
        f"Are you sure you want to release <b>{poke.display_name}</b> "
        f"(Lv.{poke.level}, {poke.iv_percentage}% IV)?\n"
        "This cannot be undone!",
        reply_markup=builder.as_markup(),
    )


@router.callback_query(lambda c: c.data and c.data.startswith("release:"))
async def callback_release(
    callback: CallbackQuery, session: AsyncSession, user: User
) -> None:
    """Handle release confirmation callbacks."""
    if not callback.data:
        return

    action = callback.data.split(":")[1]

    if action == "cancel":
        await callback.message.edit_text("Release cancelled.")
        await callback.answer()
        return

    if action == "confirm":
        pokemon_id = callback.data.split(":")[2]

        result = await session.execute(
            select(Pokemon)
            .where(Pokemon.owner_id == user.telegram_id)
            .where(Pokemon.id == pokemon_id)
        )
        poke = result.scalar_one_or_none()

        if not poke or not poke.is_releasable:
            await callback.message.edit_text("Pokemon not found or cannot be released.")
            await callback.answer()
            return

        name = poke.display_name
        await session.delete(poke)
        await session.commit()

        await callback.message.edit_text(f"Goodbye, <b>{name}</b>...")
        await callback.answer("Released!")


@router.callback_query(lambda c: c.data and c.data.startswith("pokemon:page:"))
async def callback_pokemon_page(
    callback: CallbackQuery, session: AsyncSession, user: User
) -> None:
    """Handle Pokemon list pagination callbacks."""
    if not callback.data:
        return

    page = int(callback.data.split(":")[2])

    # Rebuild the query (default filters, just pagination)
    query = (
        select(Pokemon)
        .where(Pokemon.owner_id == user.telegram_id)
        .join(PokemonSpecies, Pokemon.species_id == PokemonSpecies.national_dex)
        .order_by(Pokemon.caught_at.desc())
    )

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await session.execute(count_query)
    total_count = total_result.scalar() or 0

    total_pages = (total_count + POKEMON_PER_PAGE - 1) // POKEMON_PER_PAGE
    page = max(1, min(page, total_pages))
    offset = (page - 1) * POKEMON_PER_PAGE

    result = await session.execute(query.offset(offset).limit(POKEMON_PER_PAGE))
    pokemon_list = result.scalars().all()

    lines = [f"<b>Your Pokemon</b> ({total_count} total)\n"]

    for i, poke in enumerate(pokemon_list):
        idx = offset + i + 1
        shiny = "✨ " if poke.is_shiny else ""
        fav = "❤️ " if poke.is_favorite else ""
        
        if poke.nickname:
            name = f"{poke.nickname} ({poke.species.name})"
        else:
            name = poke.species.name

        iv_pct = poke.iv_percentage
        selected = " ◀️" if str(poke.id) == user.selected_pokemon_id else ""

        lines.append(
            f"{idx}. {shiny}{fav}<b>{name}</b> "
            f"Lv.{poke.level} | {iv_pct}% IV{selected}"
        )

    if total_pages > 1:
        lines.append(f"\nPage {page}/{total_pages}")

    builder = InlineKeyboardBuilder()
    if page > 1:
        builder.button(text="◀️ Prev", callback_data=f"pokemon:page:{page - 1}")
    if page < total_pages:
        builder.button(text="Next ▶️", callback_data=f"pokemon:page:{page + 1}")
    builder.adjust(2)

    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=builder.as_markup() if total_pages > 1 else None,
    )
    await callback.answer()


@router.message(Command("evolve"))
async def cmd_evolve(message: Message, session: AsyncSession, user: User) -> None:
    """Handle /evolve command to evolve a Pokemon."""
    text = message.text or ""
    args = text.split()

    # Get Pokemon list for user
    result = await session.execute(
        select(Pokemon)
        .where(Pokemon.owner_id == user.telegram_id)
        .order_by(Pokemon.caught_at.desc())
    )
    pokemon_list = result.scalars().all()

    if not pokemon_list:
        await message.answer("You don't have any Pokemon!")
        return

    # Parse Pokemon index and optional item
    pokemon_idx = None
    item_name = None

    if len(args) >= 2:
        # First arg could be index or item name
        if args[1].isdigit():
            pokemon_idx = int(args[1])
            if len(args) >= 3:
                item_name = " ".join(args[2:])
        else:
            # No index specified, use selected pokemon
            item_name = " ".join(args[1:])

    # Get the target pokemon
    if pokemon_idx:
        if pokemon_idx < 1 or pokemon_idx > len(pokemon_list):
            await message.answer(f"Invalid Pokemon ID! You have {len(pokemon_list)} Pokemon.")
            return
        poke = pokemon_list[pokemon_idx - 1]
    elif user.selected_pokemon_id:
        # Use selected pokemon
        sel_result = await session.execute(
            select(Pokemon)
            .where(Pokemon.id == user.selected_pokemon_id)
            .where(Pokemon.owner_id == user.telegram_id)
        )
        poke = sel_result.scalar_one_or_none()
        if not poke:
            await message.answer("Your selected Pokemon was not found. Use /evolve [number]")
            return
    else:
        await message.answer(
            "Please specify a Pokemon to evolve!\n"
            "Usage: /evolve [number] [item name]\n"
            "Example: /evolve 1\n"
            "Example: /evolve 1 fire stone"
        )
        return

    # Check evolution possibilities
    evo_result = await check_evolution(
        session, poke, user.telegram_id, use_item=item_name
    )

    if evo_result.can_evolve:
        # Attempt evolution
        success, message_text = await evolve_pokemon(
            session, poke, user.telegram_id, use_item=item_name
        )

        if success:
            # Refresh the Pokemon data
            await session.refresh(poke)

            # Update quest progress
            from telemon.core.quests import update_quest_progress
            completed = await update_quest_progress(session, user.telegram_id, "evolve")
            quest_text = ""
            if completed:
                await session.commit()
                for q in completed:
                    quest_text += f"\n📋 Quest complete: {q.description} (+{q.reward_coins:,} TC)"
            
            # Achievement hooks
            user.total_evolutions += 1
            from telemon.core.achievements import check_achievements, format_achievement_notification
            new_achs = await check_achievements(session, user.telegram_id, "evolve")
            ach_text = format_achievement_notification(new_achs)
            if new_achs:
                await session.commit()

            await message.answer(
                f"<b>Congratulations!</b>\n\n"
                f"{message_text}\n\n"
                f"Your Pokemon is now a <b>{poke.species.name}</b>!{quest_text}{ach_text}"
            )
            
            logger.info(
                "Pokemon evolved successfully",
                user_id=user.telegram_id,
                pokemon_id=str(poke.id),
                new_species=poke.species.name,
            )
        else:
            await message.answer(f"Evolution failed: {message_text}")
    else:
        # Show evolution requirements
        evolutions = get_possible_evolutions(poke.species_id)
        
        if not evolutions:
            await message.answer(
                f"<b>{poke.species.name}</b> cannot evolve."
            )
            return

        lines = [f"<b>{poke.species.name}</b> Evolution Info\n"]
        
        if evo_result.evolved_species_name:
            lines.append(f"Evolves to: <b>{evo_result.evolved_species_name}</b>")
            lines.append(f"Requirement: {evo_result.requirement}")
            lines.append(f"\n{evo_result.missing_requirement}")
        else:
            lines.append(evo_result.missing_requirement or "Cannot evolve.")

        # Show available evolutions
        if len(evolutions) > 1:
            lines.append("\n<b>Possible Evolutions:</b>")
            for evo in evolutions:
                trigger = evo["trigger"]
                if trigger == "level":
                    lines.append(f"  Level {evo.get('min_level', '?')}+")
                elif trigger == "item":
                    lines.append(f"  {evo.get('item', 'Unknown item').title()}")
                elif trigger == "trade":
                    lines.append(f"  Trade")
                elif trigger == "friendship":
                    lines.append(f"  High Friendship")

        await message.answer("\n".join(lines))
