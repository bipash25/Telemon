"""Profile and user-related handlers."""

from datetime import datetime, timedelta

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from telemon.config import settings
from telemon.database.models import PokedexEntry, Pokemon, User

router = Router(name="profile")


@router.message(Command("profile"))
async def cmd_profile(message: Message, session: AsyncSession, user: User) -> None:
    """Handle /profile command."""
    # Get actual stats
    poke_result = await session.execute(
        select(func.count(Pokemon.id)).where(Pokemon.owner_id == user.telegram_id)
    )
    pokemon_count = poke_result.scalar() or 0

    unique_result = await session.execute(
        select(func.count(PokedexEntry.species_id))
        .where(PokedexEntry.user_id == user.telegram_id)
        .where(PokedexEntry.caught == True)
    )
    unique_caught = unique_result.scalar() or 0

    shiny_result = await session.execute(
        select(func.count(Pokemon.id))
        .where(Pokemon.owner_id == user.telegram_id)
        .where(Pokemon.is_shiny == True)
    )
    shiny_count = shiny_result.scalar() or 0

    # Selected Pokemon info
    selected_text = "<i>None selected</i>"
    if user.selected_pokemon_id:
        sel_result = await session.execute(
            select(Pokemon)
            .where(Pokemon.id == user.selected_pokemon_id)
            .where(Pokemon.owner_id == user.telegram_id)
        )
        sel_poke = sel_result.scalar_one_or_none()
        if sel_poke:
            shiny_mark = " ✨" if sel_poke.is_shiny else ""
            selected_text = f"{sel_poke.display_name}{shiny_mark} Lv.{sel_poke.level} | Friendship: {sel_poke.friendship}/255"

    profile_text = (
        f"<b>Trainer Profile</b>\n\n"
        f"<b>Name:</b> {user.display_name}\n"
        f"<b>Balance:</b> {user.balance:,} Telecoins\n\n"
        f"<b>Pokemon Stats</b>\n"
        f"  Total Caught: {pokemon_count}\n"
        f"  Unique Species: {unique_caught}\n"
        f"  Shinies: {shiny_count}\n\n"
        f"<b>Battle Stats</b>\n"
        f"  Wins: {user.battle_wins}\n"
        f"  Losses: {user.battle_losses}\n"
        f"  Win Rate: {user.win_rate:.1f}%\n"
        f"  Rating: {user.battle_rating}\n\n"
        f"<b>Selected Pokemon:</b> {selected_text}\n"
        f"<b>Daily Streak:</b> {user.daily_streak} days\n\n"
        f"<i>Trainer since {user.created_at.strftime('%B %d, %Y')}</i>"
    )
    await message.answer(profile_text)


@router.message(Command("balance", "bal"))
async def cmd_balance(message: Message, user: User) -> None:
    """Handle /balance command."""
    await message.answer(f"<b>Balance:</b> {user.balance:,} Telecoins")


@router.message(Command("daily"))
async def cmd_daily(message: Message, session: AsyncSession, user: User) -> None:
    """Handle /daily command for daily rewards."""
    now = datetime.utcnow()

    # Check if already claimed today
    if user.last_daily:
        time_since_last = now - user.last_daily
        if time_since_last < timedelta(hours=20):
            # Already claimed
            next_claim = user.last_daily + timedelta(hours=20)
            remaining = next_claim - now
            hours = int(remaining.total_seconds() // 3600)
            minutes = int((remaining.total_seconds() % 3600) // 60)
            await message.answer(
                f"You've already claimed your daily reward!\n"
                f"Next claim in: <b>{hours}h {minutes}m</b>"
            )
            return

        # Check if streak should reset (more than 48 hours)
        if time_since_last > timedelta(hours=48):
            user.daily_streak = 0

    # Calculate reward with streak bonus
    streak = min(user.daily_streak, settings.daily_streak_max)
    base_reward = settings.daily_reward_base
    streak_bonus = streak * settings.daily_streak_bonus
    total_reward = base_reward + streak_bonus

    # Update user
    user.balance += total_reward
    user.daily_streak += 1
    user.last_daily = now

    # Friendship bonus: selected Pokemon gets friendship
    friendship_text = ""
    if user.selected_pokemon_id:
        sel_result = await session.execute(
            select(Pokemon)
            .where(Pokemon.id == user.selected_pokemon_id)
            .where(Pokemon.owner_id == user.telegram_id)
        )
        sel_poke = sel_result.scalar_one_or_none()
        if sel_poke and sel_poke.friendship < 255:
            gain = 5
            if sel_poke.held_item and sel_poke.held_item.lower() == "soothe bell":
                gain *= 2
            old = sel_poke.friendship
            sel_poke.friendship = min(255, sel_poke.friendship + gain)
            actual = sel_poke.friendship - old
            friendship_text = f"\n{sel_poke.display_name}: +{actual} friendship ({sel_poke.friendship}/255)"

    await session.commit()

    # Update quest progress for daily claim
    from telemon.core.quests import update_quest_progress

    daily_quest_msg = ""
    completed = await update_quest_progress(session, user.telegram_id, "daily_claim")
    if completed:
        await session.commit()
        for q in completed:
            daily_quest_msg += f"\n📋 Quest complete: {q.description} (+{q.reward_coins:,} TC)"

    streak_text = ""
    if streak > 0:
        streak_text = f"\nStreak bonus: +{streak_bonus} ({streak} days)"

    await message.answer(
        f"<b>Daily Reward Claimed!</b>\n\n"
        f"+{base_reward} Telecoins{streak_text}\n"
        f"Total: <b>+{total_reward}</b> Telecoins\n\n"
        f"New balance: {user.balance:,} Telecoins\n"
        f"Current streak: {user.daily_streak} days{friendship_text}{daily_quest_msg}"
    )
