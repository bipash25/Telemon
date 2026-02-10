"""Achievements command handler."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from telemon.core.achievements import ACHIEVEMENTS
from telemon.database.models.achievement import UserAchievement
from telemon.database.models.user import User

router = Router(name="achievements")

# Categories for display ordering
CATEGORY_ORDER = [
    ("catch", "Catching"),
    ("shiny", "Shiny"),
    ("pokedex", "Pokedex"),
    ("evolution", "Evolution"),
    ("battle", "Battle"),
    ("trade", "Trading"),
    ("streak", "Daily Streak"),
    ("special", "Special"),
    ("wonder", "Wonder Trade"),
]


@router.message(Command("achievements", "badges", "ach"))
async def cmd_achievements(
    message: Message, session: AsyncSession, user: User
) -> None:
    """Show the user's achievement progress."""
    # Get unlocked achievement IDs
    result = await session.execute(
        select(UserAchievement.achievement_id).where(
            UserAchievement.user_id == user.telegram_id
        )
    )
    unlocked = set(result.scalars().all())

    total = len(ACHIEVEMENTS)
    earned = len(unlocked)

    lines = [
        f"<b>Achievements</b> — {earned}/{total}\n",
    ]

    for cat_id, cat_name in CATEGORY_ORDER:
        cat_achs = [
            (aid, ach)
            for aid, ach in ACHIEVEMENTS.items()
            if ach["category"] == cat_id
        ]
        if not cat_achs:
            continue

        cat_earned = sum(1 for aid, _ in cat_achs if aid in unlocked)
        lines.append(f"\n<b>{cat_name}</b> ({cat_earned}/{len(cat_achs)})")

        for aid, ach in cat_achs:
            if aid in unlocked:
                mark = "+"
            else:
                mark = "-"
            reward_str = f"{ach['reward']:,}"
            lines.append(
                f"  [{mark}] {ach['name']} — {ach['desc']} ({reward_str} TC)"
            )

    # Total rewards
    total_tc = sum(
        ach["reward"] for aid, ach in ACHIEVEMENTS.items() if aid in unlocked
    )
    lines.append(f"\n<b>Total earned:</b> {total_tc:,} TC from achievements")

    await message.answer("\n".join(lines))
