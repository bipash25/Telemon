"""Start and welcome handlers."""

from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from telemon.database.models import User

router = Router(name="start")


WELCOME_MESSAGE = """
<b>Welcome to Telemon!</b> 

A Pokemon-style game right here on Telegram!

<b>What can you do?</b>
 Catch wild Pokemon that spawn in group chats
 Build your collection and train them
 Battle other trainers in PvP duels
 Trade Pokemon and items with friends
 Buy and sell on the global market

<b>Quick Start:</b>
1. Add me to a group chat
2. Chat with friends - Pokemon will spawn!
3. Use /catch &lt;name&gt; to catch them
4. Use /pokemon to see your collection

<b>Need help?</b> Use /help to see all commands.

<i>Good luck, Trainer!</i>
"""

RETURNING_MESSAGE = """
<b>Welcome back, {name}!</b>

 Pokemon caught: <b>{pokemon_count}</b>
 Balance: <b>{balance}</b> Telecoins

Use /pokemon to manage your collection or /help for commands.
"""


@router.message(CommandStart())
async def cmd_start(message: Message, session: AsyncSession, user: User) -> None:
    """Handle /start command."""
    # Check if user is new or returning
    if user.created_at == user.updated_at:
        # New user
        await message.answer(WELCOME_MESSAGE)
    else:
        # Returning user - get their pokemon count
        pokemon_count = 0  # TODO: Get actual count from repository
        await message.answer(
            RETURNING_MESSAGE.format(
                name=user.display_name,
                pokemon_count=pokemon_count,
                balance=user.balance,
            )
        )


@router.message(Command("ping"))
async def cmd_ping(message: Message) -> None:
    """Simple ping command to test bot responsiveness."""
    await message.answer("Pong!")
