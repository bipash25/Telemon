"""Pokemon collection handlers."""

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from telemon.database.models import Pokemon, PokemonSpecies, User

router = Router(name="pokemon")

POKEMON_PER_PAGE = 15


def parse_pokemon_args(text: str) -> dict:
    """Parse filter and sort arguments from command."""
    args = {
        "shiny": False,
        "legendary": False,
        "name": None,
        "type": None,
        "order": "recent",
        "page": 1,
    }

    if not text:
        return args

    parts = text.split()
    i = 0
    while i < len(parts):
        part = parts[i].lower()
        if part == "--shiny":
            args["shiny"] = True
        elif part == "--legendary":
            args["legendary"] = True
        elif part == "--name" and i + 1 < len(parts):
            i += 1
            args["name"] = parts[i].lower()
        elif part == "--type" and i + 1 < len(parts):
            i += 1
            args["type"] = parts[i].lower()
        elif part == "--order" and i + 1 < len(parts):
            i += 1
            args["order"] = parts[i].lower()
        i += 1

    return args


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
    if args["name"]:
        query = query.where(PokemonSpecies.name_lower.contains(args["name"]))
    if args["type"]:
        query = query.where(
            (PokemonSpecies.type1 == args["type"]) | (PokemonSpecies.type2 == args["type"])
        )

    # Apply sorting
    if args["order"] == "iv":
        # Sort by IV total (calculated)
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
    elif args["order"] == "level":
        query = query.order_by(Pokemon.level.desc())
    else:  # recent
        query = query.order_by(Pokemon.caught_at.desc())

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await session.execute(count_query)
    total_count = total_result.scalar() or 0

    if total_count == 0:
        if args["shiny"] or args["legendary"] or args["name"] or args["type"]:
            await message.answer(" No Pokemon match your filters.")
        else:
            await message.answer(
                " You don't have any Pokemon yet!\n"
                "Catch some in group chats with /catch"
            )
        return

    # Paginate
    page = args["page"]
    offset = (page - 1) * POKEMON_PER_PAGE
    query = query.offset(offset).limit(POKEMON_PER_PAGE)

    result = await session.execute(query)
    pokemon_list = result.scalars().all()

    # Build response
    lines = [f"<b>Your Pokemon</b> ({total_count} total)\n"]

    for i, poke in enumerate(pokemon_list):
        idx = offset + i + 1
        shiny = "" if poke.is_shiny else ""
        fav = "" if poke.is_favorite else ""
        name = poke.nickname or poke.species.name
        iv_pct = poke.iv_percentage

        lines.append(
            f"{idx}. {shiny}{fav}<b>{name}</b> "
            f"Lv.{poke.level} | {iv_pct}% IV"
        )

    # Pagination info
    total_pages = (total_count + POKEMON_PER_PAGE - 1) // POKEMON_PER_PAGE
    if total_pages > 1:
        lines.append(f"\nPage {page}/{total_pages}")

    # Build pagination keyboard
    builder = InlineKeyboardBuilder()
    if page > 1:
        builder.button(text="◀️ Prev", callback_data=f"pokemon:page:{page - 1}")
    if page < total_pages:
        builder.button(text="Next ▶️", callback_data=f"pokemon:page:{page + 1}")
    builder.adjust(2)

    await message.answer("\n".join(lines), reply_markup=builder.as_markup())


@router.message(Command("info"))
async def cmd_info(message: Message, session: AsyncSession, user: User) -> None:
    """Handle /info command to show Pokemon details."""
    # Parse Pokemon ID from args
    text = message.text or ""
    args = text.split()

    if len(args) < 2:
        # Show info for selected Pokemon
        if not user.selected_pokemon_id:
            await message.answer(
                " Please specify a Pokemon ID or select one with /select"
            )
            return
        pokemon_id = user.selected_pokemon_id
    else:
        pokemon_id = args[1]

    # Get Pokemon
    result = await session.execute(
        select(Pokemon)
        .where(Pokemon.owner_id == user.telegram_id)
        .where(Pokemon.id == pokemon_id)
    )
    poke = result.scalar_one_or_none()

    if not poke:
        await message.answer(" Pokemon not found!")
        return

    # Build detailed info
    shiny = " SHINY" if poke.is_shiny else ""
    fav = " " if poke.is_favorite else ""

    type_text = poke.species.type1.capitalize()
    if poke.species.type2:
        type_text += f"/{poke.species.type2.capitalize()}"

    info = f"""
<b>{poke.display_name}</b>{shiny}{fav}
{poke.species.name} #{poke.species.national_dex}

<b>Type:</b> {type_text}
<b>Level:</b> {poke.level}
<b>Nature:</b> {poke.nature.capitalize()}
<b>Ability:</b> {poke.ability or "Unknown"}

<b>IVs</b> ({poke.iv_percentage}% total)
HP: {poke.iv_hp} | Atk: {poke.iv_attack} | Def: {poke.iv_defense}
SpA: {poke.iv_sp_attack} | SpD: {poke.iv_sp_defense} | Spe: {poke.iv_speed}

<b>EVs</b> ({poke.ev_total}/510)
HP: {poke.ev_hp} | Atk: {poke.ev_attack} | Def: {poke.ev_defense}
SpA: {poke.ev_sp_attack} | SpD: {poke.ev_sp_defense} | Spe: {poke.ev_speed}

<b>Moves:</b> {', '.join(poke.moves) if poke.moves else 'None'}
<b>Held Item:</b> {poke.held_item or 'None'}
<b>Friendship:</b> {poke.friendship}/255

<i>Caught {poke.caught_at.strftime('%Y-%m-%d')}</i>
"""

    await message.answer(info)


@router.message(Command("select"))
async def cmd_select(message: Message, session: AsyncSession, user: User) -> None:
    """Handle /select command to set active Pokemon."""
    text = message.text or ""
    args = text.split()

    if len(args) < 2:
        await message.answer(" Usage: /select <pokemon_id>")
        return

    pokemon_id = args[1]

    # Verify ownership
    result = await session.execute(
        select(Pokemon)
        .where(Pokemon.owner_id == user.telegram_id)
        .where(Pokemon.id == pokemon_id)
    )
    poke = result.scalar_one_or_none()

    if not poke:
        await message.answer(" Pokemon not found!")
        return

    user.selected_pokemon_id = str(poke.id)
    await session.commit()

    await message.answer(f" Selected <b>{poke.display_name}</b> as your active Pokemon!")


@router.message(Command("nickname"))
async def cmd_nickname(message: Message, session: AsyncSession, user: User) -> None:
    """Handle /nickname command to rename Pokemon."""
    text = message.text or ""
    args = text.split(maxsplit=2)

    if len(args) < 3:
        await message.answer(" Usage: /nickname <pokemon_id> <new_name>")
        return

    pokemon_id = args[1]
    new_name = args[2][:50]  # Limit to 50 chars

    # Verify ownership
    result = await session.execute(
        select(Pokemon)
        .where(Pokemon.owner_id == user.telegram_id)
        .where(Pokemon.id == pokemon_id)
    )
    poke = result.scalar_one_or_none()

    if not poke:
        await message.answer(" Pokemon not found!")
        return

    old_name = poke.display_name
    poke.nickname = new_name
    await session.commit()

    await message.answer(f" Renamed <b>{old_name}</b> to <b>{new_name}</b>!")


@router.message(Command("favorite"))
async def cmd_favorite(message: Message, session: AsyncSession, user: User) -> None:
    """Handle /favorite command to toggle favorite status."""
    text = message.text or ""
    args = text.split()

    if len(args) < 2:
        await message.answer(" Usage: /favorite <pokemon_id>")
        return

    pokemon_id = args[1]

    # Verify ownership
    result = await session.execute(
        select(Pokemon)
        .where(Pokemon.owner_id == user.telegram_id)
        .where(Pokemon.id == pokemon_id)
    )
    poke = result.scalar_one_or_none()

    if not poke:
        await message.answer(" Pokemon not found!")
        return

    poke.is_favorite = not poke.is_favorite
    await session.commit()

    if poke.is_favorite:
        await message.answer(f" <b>{poke.display_name}</b> is now a favorite!")
    else:
        await message.answer(f" <b>{poke.display_name}</b> is no longer a favorite.")


@router.message(Command("release"))
async def cmd_release(message: Message, session: AsyncSession, user: User) -> None:
    """Handle /release command to release a Pokemon."""
    text = message.text or ""
    args = text.split()

    if len(args) < 2:
        await message.answer(" Usage: /release <pokemon_id>")
        return

    pokemon_id = args[1]

    # Verify ownership
    result = await session.execute(
        select(Pokemon)
        .where(Pokemon.owner_id == user.telegram_id)
        .where(Pokemon.id == pokemon_id)
    )
    poke = result.scalar_one_or_none()

    if not poke:
        await message.answer(" Pokemon not found!")
        return

    if not poke.is_releasable:
        if poke.is_favorite:
            await message.answer(
                " This Pokemon is a favorite! "
                "Remove from favorites first with /favorite"
            )
        else:
            await message.answer(" This Pokemon cannot be released right now.")
        return

    # Build confirmation keyboard
    builder = InlineKeyboardBuilder()
    builder.button(text="Yes, release", callback_data=f"release:confirm:{poke.id}")
    builder.button(text="Cancel", callback_data="release:cancel")
    builder.adjust(2)

    await message.answer(
        f" Are you sure you want to release <b>{poke.display_name}</b>?\n"
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
        await callback.message.edit_text(" Release cancelled.")
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
            await callback.message.edit_text(" Pokemon not found or cannot be released.")
            await callback.answer()
            return

        name = poke.display_name
        await session.delete(poke)
        await session.commit()

        await callback.message.edit_text(f" Goodbye, <b>{name}</b>...")
        await callback.answer("Released!")
