"""User loading middleware."""

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
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
        session: AsyncSession | None = data.get("session")
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

        # Use upsert to avoid race conditions
        stmt = insert(User).values(
            telegram_id=user_info.id,
            username=user_info.username,
            first_name=user_info.first_name,
            last_name=user_info.last_name,
        ).on_conflict_do_update(
            index_elements=[User.telegram_id],
            set_={
                "username": user_info.username,
                "first_name": user_info.first_name,
                "last_name": user_info.last_name,
            }
        )
        await session.execute(stmt)
        await session.flush()

        # Now load the user
        result = await session.execute(
            select(User).where(User.telegram_id == user_info.id)
        )
        user = result.scalar_one()

        data["user"] = user
        return await handler(event, data)
