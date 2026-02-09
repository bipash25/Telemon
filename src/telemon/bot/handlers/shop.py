"""Shop-related handlers."""

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

router = Router(name="shop")


SHOP_MESSAGE = """
<b>Telemon Shop</b>

<b>Evolution Items</b>
 Fire Stone - 500 TC
 Water Stone - 500 TC
 Thunder Stone - 500 TC
 Leaf Stone - 500 TC
 Moon Stone - 500 TC
 Sun Stone - 500 TC

<b>Battle Items</b>
 Leftovers - 1000 TC
 Choice Band - 1500 TC
 Choice Specs - 1500 TC
 Life Orb - 2000 TC
 Focus Sash - 1000 TC

<b>Utility Items</b>
 Rare Candy - 200 TC
 Incense (1 hour) - 500 TC

<i>Use /buy &lt;item&gt; to purchase!</i>
"""


@router.message(Command("shop"))
async def cmd_shop(message: Message) -> None:
    """Handle /shop command."""
    await message.answer(SHOP_MESSAGE)


@router.message(Command("buy"))
async def cmd_buy(message: Message) -> None:
    """Handle /buy command - placeholder."""
    await message.answer(
        " <b>Shop Purchasing</b>\n\n"
        "Coming soon! You'll be able to:\n"
        "- Buy evolution stones\n"
        "- Purchase battle items\n"
        "- Get utility items like Incense\n\n"
        "<i>Stay tuned!</i>"
    )


@router.message(Command("inventory", "bag"))
async def cmd_inventory(message: Message) -> None:
    """Handle /inventory command - placeholder."""
    await message.answer(
        " <b>Your Inventory</b>\n\n"
        "You don't have any items yet!\n"
        "Visit /shop to purchase items."
    )
