"""Registration check middleware - ensures users have selected a starter Pokemon."""

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from telemon.database.models import Pokemon, User
from telemon.logging import get_logger

logger = get_logger(__name__)

# Commands that don't require registration
EXEMPT_COMMANDS = {
    "/start",
    "/help",
    "/ping",
}

# Callback prefixes that don't require registration
EXEMPT_CALLBACKS = {
    "starter:",  # Starter selection
}


class RegistrationMiddleware(BaseMiddleware):
    """Middleware to check if user has completed registration (has a starter Pokemon)."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        """Check registration status before allowing commands."""
        session: AsyncSession | None = data.get("session")
        user: User | None = data.get("user")

        # Skip if no session or user (let other middlewares handle it)
        if not session or not user:
            return await handler(event, data)

        # Check if this is an exempt command/callback
        if self._is_exempt(event):
            return await handler(event, data)

        # Check if user has any Pokemon (meaning they've selected a starter)
        result = await session.execute(
            select(func.count(Pokemon.id)).where(Pokemon.owner_id == user.telegram_id)
        )
        pokemon_count = result.scalar() or 0

        if pokemon_count == 0:
            # User hasn't registered - prompt them
            await self._send_registration_prompt(event)
            return None  # Don't process the command

        # User is registered, proceed
        return await handler(event, data)

    def _is_exempt(self, event: TelegramObject) -> bool:
        """Check if the event is exempt from registration check."""
        if isinstance(event, Message):
            # Check if it's a command
            if event.text:
                # Extract command (e.g., "/help" from "/help something")
                command = event.text.split()[0].split("@")[0].lower()
                if command in EXEMPT_COMMANDS:
                    return True
                # Non-command messages in groups are exempt (for spawn tracking)
                if not event.text.startswith("/"):
                    return True
        elif isinstance(event, CallbackQuery):
            # Check callback data prefix
            if event.data:
                for prefix in EXEMPT_CALLBACKS:
                    if event.data.startswith(prefix):
                        return True

        return False

    async def _send_registration_prompt(self, event: TelegramObject) -> None:
        """Send a prompt to register."""
        message = (
            "You haven't started your Pokemon journey yet!\n\n"
            "Use /start to choose your starter Pokemon and begin."
        )

        if isinstance(event, Message):
            await event.answer(message)
        elif isinstance(event, CallbackQuery):
            await event.answer(message, show_alert=True)
