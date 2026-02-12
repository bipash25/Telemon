"""Mega Evolution info command handler."""

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from telemon.core.forms import (
    can_mega_evolve,
    can_rayquaza_mega,
    get_mega_forms,
    get_all_mega_species,
    MEGA_CAPABLE_SPECIES,
)
from telemon.database.models import Pokemon, User
from telemon.logging import get_logger

router = Router(name="mega")
logger = get_logger(__name__)


@router.message(Command("mega"))
async def cmd_mega(message: Message, session: AsyncSession, user: User) -> None:
    """Show mega evolution info for selected Pokemon, or list all mega-capable species."""
    text = message.text or ""
    args = text.split()

    # /mega list — show all mega-capable species
    if len(args) >= 2 and args[1].lower() == "list":
        all_megas = get_all_mega_species()

        lines = [
            "<b>Mega Evolution List</b>\n",
            f"<b>{len(all_megas)}</b> mega evolutions available:\n",
        ]

        for entry in all_megas:
            stone = entry.get("mega_stone_display")
            if stone:
                lines.append(
                    f"  #{entry['species_id']:04d} {entry['species_name']} → "
                    f"<b>{entry['form_name']}</b> ({stone})"
                )
            else:
                lines.append(
                    f"  #{entry['species_id']:04d} {entry['species_name']} → "
                    f"<b>{entry['form_name']}</b> (Dragon Ascent)"
                )

        lines.append(
            "\n<i>Buy mega stones from /shop and give them to "
            "your Pokemon with /give [#] [stone name].\n"
            "Then use Mega Evolve during battle!</i>"
        )

        await message.answer("\n".join(lines))
        return

    # /mega (no args) — show info for selected Pokemon
    if not user.selected_pokemon_id:
        await message.answer(
            "<b>Mega Evolution</b>\n\n"
            "Check if your Pokemon can mega evolve!\n\n"
            "<b>Usage:</b>\n"
            "/mega - Check selected Pokemon\n"
            "/mega list - List all mega evolutions\n\n"
            "<i>Select a Pokemon first with /select [#]</i>"
        )
        return

    poke_result = await session.execute(
        select(Pokemon).where(Pokemon.id == user.selected_pokemon_id)
    )
    poke = poke_result.scalar_one_or_none()

    if not poke:
        await message.answer("Your selected Pokemon was not found!")
        return

    # Check if species can mega evolve at all
    forms = get_mega_forms(poke.species_id)
    if not forms:
        await message.answer(
            f"<b>{poke.display_name}</b> cannot mega evolve.\n\n"
            "Use /mega list to see all mega-capable Pokemon."
        )
        return

    # Check if currently holding the right stone
    held_lower = (poke.held_item or "").lower() if poke.held_item else None
    current_mega = can_mega_evolve(poke.species_id, held_lower)
    if not current_mega:
        current_mega = can_rayquaza_mega(poke.species_id, poke.moves)

    lines = [
        f"<b>Mega Evolution — {poke.display_name}</b>\n",
    ]

    for form in forms:
        bst = (
            form.base_hp + form.base_attack + form.base_defense +
            form.base_sp_attack + form.base_sp_defense + form.base_speed
        )
        types = form.type1.title()
        if form.type2:
            types += f" / {form.type2.title()}"

        lines.append(f"<b>{form.form_name}</b>")
        lines.append(f"  Type: {types}")
        lines.append(f"  Ability: {form.ability}")
        lines.append(
            f"  Stats: {form.base_hp}/{form.base_attack}/{form.base_defense}/"
            f"{form.base_sp_attack}/{form.base_sp_defense}/{form.base_speed}"
            f" (BST: {bst})"
        )
        if form.mega_stone_display:
            lines.append(f"  Requires: {form.mega_stone_display}")
        else:
            lines.append("  Requires: Dragon Ascent move")
        lines.append("")

    if current_mega:
        lines.append(
            f"<b>Ready to mega evolve into {current_mega.form_name}!</b>\n"
            "Use the Mega Evolve button during battle."
        )
    else:
        if poke.species_id == 384:
            lines.append(
                "<i>Teach your Rayquaza Dragon Ascent to mega evolve.</i>"
            )
        else:
            stone_names = [f.mega_stone_display for f in forms if f.mega_stone_display]
            lines.append(
                f"<i>Give your {poke.species.name} a "
                f"{' or '.join(stone_names)} to mega evolve in battle.\n"
                f"Use /give [#] [stone name] after buying from /shop.</i>"
            )

    await message.answer("\n".join(lines))
