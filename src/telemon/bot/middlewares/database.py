"""Database session middleware."""

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from telemon.database import get_session_context


class DatabaseMiddleware(BaseMiddleware):
    """Middleware to provide database session to handlers."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        """Inject database session into handler data."""
        async with get_session_context() as session:
            data["session"] = session
            return await handler(event, data)
