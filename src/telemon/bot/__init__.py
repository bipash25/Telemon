"""Bot package initialization."""

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage
from redis.asyncio import Redis

from telemon.config import settings


def create_bot() -> Bot:
    """Create and configure the Telegram bot."""
    return Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(
            parse_mode=ParseMode.HTML,
            link_preview_is_disabled=True,
        ),
    )


async def create_dispatcher() -> Dispatcher:
    """Create and configure the dispatcher with FSM storage."""
    # Redis storage for FSM
    redis = Redis.from_url(str(settings.redis_url))
    storage = RedisStorage(redis=redis)

    dp = Dispatcher(storage=storage)

    # Register handlers
    from telemon.bot.handlers import register_all_handlers

    register_all_handlers(dp)

    # Register middlewares
    from telemon.bot.middlewares import register_all_middlewares

    register_all_middlewares(dp)

    return dp


__all__ = ["create_bot", "create_dispatcher"]
