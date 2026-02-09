"""Market-related handlers."""

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

router = Router(name="market")


@router.message(Command("market"))
async def cmd_market(message: Message) -> None:
    """Handle /market command - placeholder."""
    await message.answer(
        " <b>Global Marketplace</b>\n\n"
        "Coming soon! The marketplace will allow you to:\n"
        "- Browse Pokemon listings from all trainers\n"
        "- Buy Pokemon with Telecoins\n"
        "- Sell your Pokemon to others\n"
        "- Filter by name, type, IV, shiny, etc.\n\n"
        "<i>Stay tuned!</i>"
    )
