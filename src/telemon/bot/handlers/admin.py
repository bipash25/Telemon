"""Admin and group settings handlers."""

from aiogram import Bot, Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from telemon.core.spawning import create_spawn, get_random_species
from telemon.database.models import ActiveSpawn, Group, PokemonSpecies
from telemon.logging import get_logger

router = Router(name="admin")
logger = get_logger(__name__)


@router.message(Command("settings"))
async def cmd_settings(message: Message, session: AsyncSession) -> None:
    """Handle /settings command for group admins."""
    # Check if in group
    if message.chat.type == "private":
        await message.answer(" This command only works in groups!")
        return

    # Check if user is admin
    chat_member = await message.chat.get_member(message.from_user.id)
    if chat_member.status not in ("administrator", "creator"):
        await message.answer(" Only group admins can use this command!")
        return

    # Get or create group settings
    result = await session.execute(
        select(Group).where(Group.chat_id == message.chat.id)
    )
    group = result.scalar_one_or_none()

    if not group:
        group = Group(
            chat_id=message.chat.id,
            title=message.chat.title,
        )
        session.add(group)
        await session.commit()

    settings_text = f"""
<b>Group Settings</b>
{message.chat.title}

<b>Spawning</b>
Enabled: {'Yes' if group.spawn_enabled else 'No'}
Spawn Threshold: {group.spawn_threshold} messages
Spawn Channel: {'Set' if group.spawn_channel_id else 'Not set'}

<b>Features</b>
Battles Enabled: {'Yes' if group.battles_enabled else 'No'}
Language: {group.language.upper()}

<b>Stats</b>
Total Spawns: {group.total_spawns}
Total Catches: {group.total_catches}

<i>Use inline buttons below to change settings.</i>
"""
    # TODO: Add inline keyboard for settings
    await message.answer(settings_text)


@router.message(Command("spawn"))
async def cmd_spawn(message: Message, session: AsyncSession, bot: Bot) -> None:
    """Handle /spawn command to force a Pokemon spawn."""
    # Check if in group
    if message.chat.type == "private":
        await message.answer("This command only works in groups!")
        return

    # Check if user is admin
    if message.from_user:
        chat_member = await message.chat.get_member(message.from_user.id)
        if chat_member.status not in ("administrator", "creator"):
            await message.answer("Only group admins can use this command!")
            return

    chat_id = message.chat.id
    
    # Get or create group
    result = await session.execute(
        select(Group).where(Group.chat_id == chat_id)
    )
    group = result.scalar_one_or_none()
    
    if not group:
        group = Group(
            chat_id=chat_id,
            title=message.chat.title,
        )
        session.add(group)
        await session.flush()

    # Check for existing active spawn
    from datetime import datetime
    result = await session.execute(
        select(ActiveSpawn)
        .where(ActiveSpawn.chat_id == chat_id)
        .where(ActiveSpawn.caught_by.is_(None))
        .where(ActiveSpawn.expires_at > datetime.utcnow())
    )
    existing = result.scalar_one_or_none()
    
    if existing:
        await message.answer(
            "There's already an active spawn in this group!\n"
            "Use /catch <name> to catch it first."
        )
        return

    # Get random species
    species = await get_random_species(session)
    if not species:
        await message.answer("No Pokemon species found in database!")
        return

    # Create spawn (without message_id for now)
    spawn = await create_spawn(
        session=session,
        chat_id=chat_id,
        message_id=0,  # Will update after sending
        species=species,
    )

    if not spawn:
        await message.answer("Failed to create spawn!")
        return

    # Build spawn message
    from telemon.config import settings
    shiny_text = " (SHINY!)" if spawn.is_shiny else ""
    rarity_emoji = _get_rarity_emoji(species)

    caption = (
        f"{rarity_emoji} <b>A wild Pokemon has appeared!</b>{shiny_text}\n\n"
        f"Use <code>/catch &lt;name&gt;</code> to catch it!\n"
        f"Use <code>/hint</code> if you need help.\n\n"
        f"<i>It will flee in {settings.spawn_timeout_seconds // 60} minutes...</i>"
    )

    try:
        # Try to send with image
        if species.sprite_url:
            msg = await bot.send_photo(
                chat_id=chat_id,
                photo=species.sprite_url,
                caption=caption,
            )
        else:
            msg = await bot.send_message(
                chat_id=chat_id,
                text=caption,
            )
        
        # Update spawn with message ID
        spawn.message_id = msg.message_id
        await session.commit()
        
        logger.info(
            "Admin force spawned Pokemon",
            chat_id=chat_id,
            species=species.name,
            is_shiny=spawn.is_shiny,
            admin_id=message.from_user.id if message.from_user else None,
        )
    except Exception as e:
        logger.error("Failed to send spawn message", error=str(e), chat_id=chat_id)
        await message.answer(f"Failed to send spawn message: {e}")


def _get_rarity_emoji(species: PokemonSpecies) -> str:
    """Get emoji based on Pokemon rarity."""
    if species.is_mythical:
        return "MYTHICAL"
    if species.is_legendary:
        return "LEGENDARY"
    if species.catch_rate <= 3:
        return "ULTRA RARE"
    if species.catch_rate <= 45:
        return "RARE"
    if species.catch_rate <= 120:
        return "UNCOMMON"
    return "COMMON"
