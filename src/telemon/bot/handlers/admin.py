"""Admin and group settings handlers."""

from datetime import datetime

from aiogram import Bot, Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from telemon.core.spawning import create_spawn, get_random_species
from telemon.database.models import ActiveSpawn, Group, PokemonSpecies, SpawnAdmin
from telemon.logging import get_logger

router = Router(name="admin")
logger = get_logger(__name__)

# Bot owner user ID - can always use spawn commands
BOT_OWNER_ID = 6894738352


async def is_spawn_admin(session: AsyncSession, user_id: int) -> bool:
    """Check if user is allowed to use /spawn command."""
    # Bot owner always has access
    if user_id == BOT_OWNER_ID:
        return True

    # Check spawn_admins table
    result = await session.execute(
        select(SpawnAdmin).where(SpawnAdmin.user_id == user_id)
    )
    return result.scalar_one_or_none() is not None


@router.message(Command("addspawner"))
async def cmd_add_spawner(message: Message, session: AsyncSession) -> None:
    """Add a user to spawn admins list. Bot owner only."""
    if not message.from_user:
        return

    # Only bot owner can add spawners
    if message.from_user.id != BOT_OWNER_ID:
        await message.answer("Only the bot owner can use this command!")
        return

    # Get target user from reply or mention
    target_user_id = None
    target_username = None

    if message.reply_to_message and message.reply_to_message.from_user:
        target_user_id = message.reply_to_message.from_user.id
        target_username = message.reply_to_message.from_user.username or str(target_user_id)
    elif message.entities:
        # Check for mentions
        for entity in message.entities:
            if entity.type == "mention":
                # Extract username from text
                mention_text = message.text[entity.offset : entity.offset + entity.length]
                target_username = mention_text.lstrip("@")
                await message.answer(
                    f"Cannot add @{target_username} - please reply to a message from the user you want to add."
                )
                return
            elif entity.type == "text_mention" and entity.user:
                target_user_id = entity.user.id
                target_username = entity.user.username or str(target_user_id)

    if not target_user_id:
        await message.answer(
            "<b>Usage:</b> Reply to a message from the user you want to add as a spawn admin.\n\n"
            "Example: Reply to someone's message and type /addspawner"
        )
        return

    # Check if already a spawn admin
    result = await session.execute(
        select(SpawnAdmin).where(SpawnAdmin.user_id == target_user_id)
    )
    existing = result.scalar_one_or_none()

    if existing:
        await message.answer(f"User {target_username} is already a spawn admin!")
        return

    # Add to spawn_admins
    spawn_admin = SpawnAdmin(
        user_id=target_user_id,
        added_by=message.from_user.id,
    )
    session.add(spawn_admin)
    await session.commit()

    await message.answer(f"Added {target_username} as a spawn admin!")
    logger.info(
        "Added spawn admin",
        user_id=target_user_id,
        added_by=message.from_user.id,
    )


@router.message(Command("removespawner"))
async def cmd_remove_spawner(message: Message, session: AsyncSession) -> None:
    """Remove a user from spawn admins list. Bot owner only."""
    if not message.from_user:
        return

    # Only bot owner can remove spawners
    if message.from_user.id != BOT_OWNER_ID:
        await message.answer("Only the bot owner can use this command!")
        return

    # Get target user from reply or mention
    target_user_id = None
    target_username = None

    if message.reply_to_message and message.reply_to_message.from_user:
        target_user_id = message.reply_to_message.from_user.id
        target_username = message.reply_to_message.from_user.username or str(target_user_id)
    elif message.entities:
        for entity in message.entities:
            if entity.type == "text_mention" and entity.user:
                target_user_id = entity.user.id
                target_username = entity.user.username or str(target_user_id)

    if not target_user_id:
        await message.answer(
            "<b>Usage:</b> Reply to a message from the user you want to remove as a spawn admin.\n\n"
            "Example: Reply to someone's message and type /removespawner"
        )
        return

    # Check if is a spawn admin
    result = await session.execute(
        select(SpawnAdmin).where(SpawnAdmin.user_id == target_user_id)
    )
    existing = result.scalar_one_or_none()

    if not existing:
        await message.answer(f"User {target_username} is not a spawn admin!")
        return

    # Remove from spawn_admins
    await session.execute(
        delete(SpawnAdmin).where(SpawnAdmin.user_id == target_user_id)
    )
    await session.commit()

    await message.answer(f"Removed {target_username} from spawn admins!")
    logger.info(
        "Removed spawn admin",
        user_id=target_user_id,
        removed_by=message.from_user.id,
    )


@router.message(Command("spawners"))
async def cmd_list_spawners(message: Message, session: AsyncSession) -> None:
    """List all spawn admins. Bot owner only."""
    if not message.from_user:
        return

    # Only bot owner can list spawners
    if message.from_user.id != BOT_OWNER_ID:
        await message.answer("Only the bot owner can use this command!")
        return

    # Get all spawn admins
    result = await session.execute(select(SpawnAdmin))
    spawn_admins = result.scalars().all()

    if not spawn_admins:
        await message.answer(
            "<b>Spawn Admins</b>\n\n"
            "No spawn admins added yet.\n\n"
            "Use /addspawner by replying to a user's message to add them."
        )
        return

    # Build list
    lines = ["<b>Spawn Admins</b>\n"]
    for i, admin in enumerate(spawn_admins, 1):
        added_at = admin.created_at.strftime("%Y-%m-%d") if admin.created_at else "Unknown"
        lines.append(f"{i}. User ID: <code>{admin.user_id}</code> (added: {added_at})")

    lines.append(f"\nTotal: {len(spawn_admins)} spawn admin(s)")
    lines.append("\nNote: Bot owner always has spawn access.")

    await message.answer("\n".join(lines))


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

    # Check if user is spawn admin (bot owner or in spawn_admins table)
    if message.from_user:
        has_permission = await is_spawn_admin(session, message.from_user.id)
        if not has_permission:
            await message.answer("You don't have permission to use /spawn!")
            return
    else:
        return

    chat_id = message.chat.id

    # Get or create group
    result = await session.execute(select(Group).where(Group.chat_id == chat_id))
    group = result.scalar_one_or_none()

    if not group:
        group = Group(
            chat_id=chat_id,
            title=message.chat.title,
            bot_joined_at=datetime.utcnow(),
        )
        session.add(group)
        await session.flush()

    # Check for existing active spawn
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
            "Use /catch [name] to catch it first."
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
            "Spawn admin force spawned Pokemon",
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
