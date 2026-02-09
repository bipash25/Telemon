"""Profile and user-related handlers."""

from datetime import datetime, timedelta

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from telemon.config import settings
from telemon.database.models import User

router = Router(name="profile")


@router.message(Command("profile"))
async def cmd_profile(message: Message, session: AsyncSession, user: User) -> None:
    """Handle /profile command."""
    # TODO: Get actual stats from repositories
    pokemon_count = 0
    unique_caught = 0
    shiny_count = 0

    profile_text = f"""
<b>Trainer Profile</b>

<b>Name:</b> {user.display_name}
<b>Balance:</b> {user.balance:,} Telecoins

<b>Pokemon Stats</b>
 Total Caught: {pokemon_count}
 Unique Species: {unique_caught}
 Shinies: {shiny_count}

<b>Battle Stats</b>
 Wins: {user.battle_wins}
 Losses: {user.battle_losses}
 Win Rate: {user.win_rate:.1f}%
 Rating: {user.battle_rating}

<b>Daily Streak:</b> {user.daily_streak} days

<i>Trainer since {user.created_at.strftime('%B %d, %Y')}</i>
"""
    await message.answer(profile_text)


@router.message(Command("balance", "bal"))
async def cmd_balance(message: Message, user: User) -> None:
    """Handle /balance command."""
    await message.answer(f" <b>Balance:</b> {user.balance:,} Telecoins")


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
                f" You've already claimed your daily reward!\n"
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

    await session.commit()

    streak_text = ""
    if streak > 0:
        streak_text = f"\n Streak bonus: +{streak_bonus} ({streak} days)"

    await message.answer(
        f"<b>Daily Reward Claimed!</b>\n\n"
        f" +{base_reward} Telecoins{streak_text}\n"
        f" Total: <b>+{total_reward}</b> Telecoins\n\n"
        f" New balance: {user.balance:,} Telecoins\n"
        f" Current streak: {user.daily_streak} days"
    )
