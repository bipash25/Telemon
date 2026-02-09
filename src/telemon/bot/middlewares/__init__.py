"""Middleware registration and implementations."""

from aiogram import Dispatcher

from telemon.bot.middlewares.database import DatabaseMiddleware
from telemon.bot.middlewares.user import UserMiddleware


def register_all_middlewares(dp: Dispatcher) -> None:
    """Register all middlewares with the dispatcher."""
    # Database session middleware (must be first)
    dp.message.middleware(DatabaseMiddleware())
    dp.callback_query.middleware(DatabaseMiddleware())

    # User loading middleware (requires database)
    dp.message.middleware(UserMiddleware())
    dp.callback_query.middleware(UserMiddleware())


__all__ = ["register_all_middlewares"]
