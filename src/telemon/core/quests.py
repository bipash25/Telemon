"""Quest system — generation, tracking, and rewards."""

import random
import uuid
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from telemon.database.models import UserQuest
from telemon.logging import get_logger

logger = get_logger(__name__)

# ──────────────────────────────────────────────
# Quest Templates
# ──────────────────────────────────────────────
# Each template defines: task, description_template, target, reward, params_gen
# description_template can use {type}, {count}, {gen} placeholders

POKEMON_TYPES = [
    "fire", "water", "grass", "electric", "ice", "fighting",
    "poison", "ground", "flying", "psychic", "bug", "rock",
    "ghost", "dragon", "dark", "steel", "fairy", "normal",
]


def _rand_type() -> str:
    return random.choice(POKEMON_TYPES)


DAILY_QUEST_POOL: list[dict[str, Any]] = [
    # Catch quests
    {"task": "catch", "desc": "Catch {count} Pokemon", "target": 3, "reward": 150, "params": {}},
    {"task": "catch", "desc": "Catch {count} Pokemon", "target": 5, "reward": 250, "params": {}},
    {"task": "catch_type", "desc": "Catch {count} {type}-type Pokemon", "target": 2, "reward": 200,
     "params_gen": lambda: {"type": _rand_type()}},
    {"task": "catch_type", "desc": "Catch {count} {type}-type Pokemon", "target": 3, "reward": 350,
     "params_gen": lambda: {"type": _rand_type()}},

    # Battle quests
    {"task": "battle_win", "desc": "Win {count} battle(s)", "target": 1, "reward": 200, "params": {}},
    {"task": "battle_win", "desc": "Win {count} battles", "target": 2, "reward": 400, "params": {}},

    # Friendship quests
    {"task": "pet", "desc": "Pet your Pokemon {count} times", "target": 5, "reward": 150, "params": {}},
    {"task": "pet", "desc": "Pet your Pokemon {count} times", "target": 10, "reward": 300, "params": {}},

    # Evolution quests
    {"task": "evolve", "desc": "Evolve {count} Pokemon", "target": 1, "reward": 300, "params": {}},

    # Trading quests
    {"task": "trade", "desc": "Complete {count} trade(s)", "target": 1, "reward": 250, "params": {}},

    # Market quests
    {"task": "market_sell", "desc": "Sell {count} Pokemon on the market", "target": 1, "reward": 200, "params": {}},

    # Misc
    {"task": "daily_claim", "desc": "Claim your daily reward", "target": 1, "reward": 50, "params": {}},
    {"task": "use_item", "desc": "Use {count} item(s)", "target": 1, "reward": 100, "params": {}},
]

WEEKLY_QUEST_POOL: list[dict[str, Any]] = [
    # Bigger catch quests
    {"task": "catch", "desc": "Catch {count} Pokemon", "target": 20, "reward": 1000, "params": {}},
    {"task": "catch", "desc": "Catch {count} Pokemon", "target": 50, "reward": 3000, "params": {}},
    {"task": "catch_type", "desc": "Catch {count} {type}-type Pokemon", "target": 10, "reward": 1500,
     "params_gen": lambda: {"type": _rand_type()}},

    # Battle quests
    {"task": "battle_win", "desc": "Win {count} battles", "target": 5, "reward": 1500, "params": {}},
    {"task": "battle_win", "desc": "Win {count} battles", "target": 10, "reward": 3000, "params": {}},

    # Evolve
    {"task": "evolve", "desc": "Evolve {count} Pokemon", "target": 3, "reward": 1000, "params": {}},

    # Friendship
    {"task": "pet", "desc": "Pet your Pokemon {count} times", "target": 30, "reward": 800, "params": {}},

    # Trade
    {"task": "trade", "desc": "Complete {count} trades", "target": 3, "reward": 1000, "params": {}},

    # Market
    {"task": "market_sell", "desc": "Sell {count} Pokemon on the market", "target": 5, "reward": 1200, "params": {}},

    # Catch shiny
    {"task": "catch_shiny", "desc": "Catch a shiny Pokemon", "target": 1, "reward": 5000, "params": {}},
]

NUM_DAILY_QUESTS = 3
NUM_WEEKLY_QUESTS = 2


# ──────────────────────────────────────────────
# Quest Generation
# ──────────────────────────────────────────────

def _next_daily_reset() -> datetime:
    """Get the next daily reset time (midnight UTC)."""
    now = datetime.utcnow()
    tomorrow = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    return tomorrow


def _next_weekly_reset() -> datetime:
    """Get the next weekly reset time (Monday midnight UTC)."""
    now = datetime.utcnow()
    days_until_monday = (7 - now.weekday()) % 7
    if days_until_monday == 0 and now.hour >= 0:
        days_until_monday = 7
    next_monday = (now + timedelta(days=days_until_monday)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    return next_monday


def _generate_quest(template: dict[str, Any], quest_type: str, expires_at: datetime) -> dict:
    """Generate a quest instance from a template."""
    params = template.get("params", {})
    if "params_gen" in template:
        params = template["params_gen"]()

    desc = template["desc"].format(
        count=template["target"],
        type=params.get("type", "").title(),
        gen=params.get("gen", ""),
    )

    return {
        "id": uuid.uuid4(),
        "quest_type": quest_type,
        "task": template["task"],
        "description": desc,
        "target_count": template["target"],
        "current_count": 0,
        "params": params if params else None,
        "reward_coins": template["reward"],
        "is_completed": False,
        "is_claimed": False,
        "expires_at": expires_at,
    }


async def get_or_create_quests(
    session: AsyncSession, user_id: int
) -> tuple[list[UserQuest], list[UserQuest]]:
    """Get user's active quests, generating new ones if expired/missing."""
    now = datetime.utcnow()

    # Clean up expired, unclaimed quests
    await session.execute(
        delete(UserQuest).where(
            UserQuest.user_id == user_id,
            UserQuest.expires_at < now,
            UserQuest.is_claimed == False,
        )
    )

    # Get current quests
    result = await session.execute(
        select(UserQuest)
        .where(UserQuest.user_id == user_id, UserQuest.expires_at >= now)
        .order_by(UserQuest.quest_type, UserQuest.created_at)
    )
    current_quests = list(result.scalars().all())

    daily_quests = [q for q in current_quests if q.quest_type == "daily"]
    weekly_quests = [q for q in current_quests if q.quest_type == "weekly"]

    # Generate daily quests if needed
    if len(daily_quests) < NUM_DAILY_QUESTS:
        needed = NUM_DAILY_QUESTS - len(daily_quests)
        # Avoid duplicating existing task types
        existing_tasks = {q.task for q in daily_quests}
        available = [t for t in DAILY_QUEST_POOL if t["task"] not in existing_tasks]
        if len(available) < needed:
            available = DAILY_QUEST_POOL  # Fall back to full pool

        selected = random.sample(available, min(needed, len(available)))
        expires = _next_daily_reset()

        for template in selected:
            quest_data = _generate_quest(template, "daily", expires)
            quest = UserQuest(user_id=user_id, **quest_data)
            session.add(quest)
            daily_quests.append(quest)

    # Generate weekly quests if needed
    if len(weekly_quests) < NUM_WEEKLY_QUESTS:
        needed = NUM_WEEKLY_QUESTS - len(weekly_quests)
        existing_tasks = {q.task for q in weekly_quests}
        available = [t for t in WEEKLY_QUEST_POOL if t["task"] not in existing_tasks]
        if len(available) < needed:
            available = WEEKLY_QUEST_POOL

        selected = random.sample(available, min(needed, len(available)))
        expires = _next_weekly_reset()

        for template in selected:
            quest_data = _generate_quest(template, "weekly", expires)
            quest = UserQuest(user_id=user_id, **quest_data)
            session.add(quest)
            weekly_quests.append(quest)

    await session.commit()
    return daily_quests, weekly_quests


# ──────────────────────────────────────────────
# Quest Progress Tracking
# ──────────────────────────────────────────────

async def update_quest_progress(
    session: AsyncSession,
    user_id: int,
    task: str,
    amount: int = 1,
    params: dict[str, Any] | None = None,
) -> list[UserQuest]:
    """
    Update progress on matching quests.

    Args:
        session: DB session
        user_id: User's Telegram ID
        task: Quest task type (e.g. "catch", "catch_type", "battle_win")
        amount: How much to increment
        params: Extra params to match (e.g. {"type": "fire"})

    Returns:
        List of quests that were completed by this update
    """
    now = datetime.utcnow()

    # Get active, uncompleted quests matching this task
    result = await session.execute(
        select(UserQuest).where(
            UserQuest.user_id == user_id,
            UserQuest.task == task,
            UserQuest.is_completed == False,
            UserQuest.expires_at >= now,
        )
    )
    matching_quests = list(result.scalars().all())

    newly_completed = []

    for quest in matching_quests:
        # Check if params match (if quest has params requirements)
        if quest.params and params:
            # For type-based quests
            if "type" in quest.params and params.get("type") != quest.params["type"]:
                continue
            if "gen" in quest.params and params.get("gen") != quest.params["gen"]:
                continue

        quest.current_count = min(quest.current_count + amount, quest.target_count)

        if quest.current_count >= quest.target_count:
            quest.is_completed = True
            quest.completed_at = now
            newly_completed.append(quest)

    # Also update generic "catch" quests when catching specific types
    if task == "catch_type":
        result2 = await session.execute(
            select(UserQuest).where(
                UserQuest.user_id == user_id,
                UserQuest.task == "catch",
                UserQuest.is_completed == False,
                UserQuest.expires_at >= now,
            )
        )
        generic_quests = list(result2.scalars().all())
        for quest in generic_quests:
            quest.current_count = min(quest.current_count + amount, quest.target_count)
            if quest.current_count >= quest.target_count:
                quest.is_completed = True
                quest.completed_at = now
                newly_completed.append(quest)

    if newly_completed:
        await session.flush()

    return newly_completed


async def claim_quest(
    session: AsyncSession, user_id: int, quest_id: str
) -> tuple[bool, str, int]:
    """
    Claim a completed quest's reward.

    Returns:
        (success, message, reward_amount)
    """
    result = await session.execute(
        select(UserQuest).where(
            UserQuest.id == quest_id,
            UserQuest.user_id == user_id,
        )
    )
    quest = result.scalar_one_or_none()

    if not quest:
        return False, "Quest not found.", 0

    if not quest.is_completed:
        return False, f"Quest not complete yet! ({quest.progress_text})", 0

    if quest.is_claimed:
        return False, "Already claimed!", 0

    quest.is_claimed = True

    return True, quest.description, quest.reward_coins
