"""Admin and group settings handlers."""

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from telemon.database.models import Group

router = Router(name="admin")


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
async def cmd_spawn(message: Message, session: AsyncSession) -> None:
    """Handle /spawn command to force a Pokemon spawn."""
    # Check if in group
    if message.chat.type == "private":
        await message.answer(" This command only works in groups!")
        return

    # Check if user is admin
    chat_member = await message.chat.get_member(message.from_user.id)
    if chat_member.status not in ("administrator", "creator"):
        await message.answer(" Only group admins can use this command!")
        return

    # TODO: Implement spawn cooldown and actual spawning
    await message.answer(
        " <b>Force Spawn</b>\n\n"
        "Coming soon! Admins will be able to:\n"
        "- Force a Pokemon spawn (with cooldown)\n"
        "- Spawn specific Pokemon (premium)\n\n"
        "<i>Stay tuned!</i>"
    )
