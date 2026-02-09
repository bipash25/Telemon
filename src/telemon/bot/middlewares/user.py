"""User loading middleware."""

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from telemon.database.models import User


class UserMiddleware(BaseMiddleware):
    """Middleware to load or create user for each request."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        """Load or create user and inject into handler data."""
        session: AsyncSession = data.get("session")
        if not session:
            # No session, skip user loading
            return await handler(event, data)

        # Get user info from event
        user_info = None
        if isinstance(event, Message) and event.from_user:
            user_info = event.from_user
        elif isinstance(event, CallbackQuery) and event.from_user:
            user_info = event.from_user

        if not user_info:
            # No user info available
            return await handler(event, data)

        # Load or create user
        result = await session.execute(
            select(User).where(User.telegram_id == user_info.id)
        )
        user = result.scalar_one_or_none()

        if not user:
            # Create new user
            user = User(
                telegram_id=user_info.id,
                username=user_info.username,
                first_name=user_info.first_name,
                last_name=user_info.last_name,
            )
            session.add(user)
            await session.flush()
        else:
            # Update user info if changed
            if user.username != user_info.username:
                user.username = user_info.username
            if user.first_name != user_info.first_name:
                user.first_name = user_info.first_name
            if user.last_name != user_info.last_name:
                user.last_name = user_info.last_name

        data["user"] = user
        return await handler(event, data)
