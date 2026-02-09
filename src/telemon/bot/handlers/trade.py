"""Trade-related handlers."""

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

router = Router(name="trade")


@router.message(Command("trade"))
async def cmd_trade(message: Message) -> None:
    """Handle /trade command - placeholder."""
    await message.answer(
        " <b>Trading System</b>\n\n"
        "Coming soon! Trading will allow you to:\n"
        "- Exchange Pokemon with other trainers\n"
        "- Trade Telecoins\n"
        "- Trigger trade evolutions\n\n"
        "<i>Stay tuned!</i>"
    )
