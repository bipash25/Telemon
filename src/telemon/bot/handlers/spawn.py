"""Spawn-related handlers - message tracking and spawn triggers."""

from datetime import datetime, timedelta

from aiogram import Bot, F, Router
from aiogram.types import Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from telemon.config import settings
from telemon.core.spawning import check_spawn_trigger, create_spawn, get_random_species
from telemon.database.models import ActiveSpawn, Group, PokedexEntry, PokemonSpecies
from telemon.logging import get_logger

router = Router(name="spawn")
logger = get_logger(__name__)


async def send_spawn_message(bot: Bot, chat_id: int, spawn: ActiveSpawn) -> int | None:
    """Send a spawn message with Pokemon image and return message ID."""
    species = spawn.species

    # Build spawn message
    shiny_text = " ✨" if spawn.is_shiny else ""
    rarity_emoji = get_rarity_emoji(species)

    caption = (
        f"{rarity_emoji} <b>A wild Pokémon has appeared!</b>{shiny_text}\n\n"
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
            # Fallback to text only
            msg = await bot.send_message(
                chat_id=chat_id,
                text=caption,
            )
        return msg.message_id
    except Exception as e:
        logger.error("Failed to send spawn message", error=str(e), chat_id=chat_id)
        return None


def get_rarity_emoji(species: PokemonSpecies) -> str:
    """Get emoji based on Pokemon rarity."""
    if species.is_mythical:
        return "🌟"
    if species.is_legendary:
        return "⭐"
    if species.catch_rate <= 3:
        return "💎"
    if species.catch_rate <= 45:
        return "🔷"
    if species.catch_rate <= 120:
        return "🔹"
    return "⚪"


@router.message(F.chat.type.in_({"group", "supergroup"}))
async def track_group_message(
    message: Message,
    session: AsyncSession,
    bot: Bot,
) -> None:
    """Track messages in groups and trigger spawns."""
    logger.info("Spawn handler triggered", chat_id=message.chat.id, chat_type=message.chat.type)
    
    chat_id = message.chat.id

    # Skip if message is a command
    if message.text and message.text.startswith("/"):
        logger.info("Skipping command message")
        return
    
    logger.info("Processing group message", chat_id=chat_id, text=message.text[:30] if message.text else "no-text")

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

    if not group.spawn_enabled:
        return

    # Increment message count
    group.message_count += 1
    logger.info(
        "Incremented message count",
        chat_id=chat_id,
        message_count=group.message_count,
        threshold=group.spawn_threshold,
    )
    
    # Flush the increment before checking spawn trigger
    await session.flush()

    # Check if we should spawn
    should_spawn = await check_spawn_trigger(session, chat_id)

    if should_spawn:
        # Get random species
        species = await get_random_species(session)
        if species:
            # Create spawn record (without message_id for now)
            spawn = await create_spawn(
                session=session,
                chat_id=chat_id,
                message_id=0,  # Will update after sending
                species=species,
            )

            if spawn:
                # Send spawn message
                msg_id = await send_spawn_message(bot, chat_id, spawn)
                if msg_id:
                    spawn.message_id = msg_id

                    # Mark Pokemon as seen for all users who might see this message
                    # For now, we'll mark it seen when users interact (catch/hint)
                    # This avoids spamming the database for every group member

                    await session.commit()

                    logger.info(
                        "Pokemon spawned",
                        chat_id=chat_id,
                        species=species.name,
                        is_shiny=spawn.is_shiny,
                    )

    await session.commit()
