"""Main entry point for Telemon bot."""

import asyncio
import sys

from telemon.bot import create_bot, create_dispatcher
from telemon.database import close_db, init_db
from telemon.logging import get_logger, setup_logging

logger = get_logger(__name__)


async def main() -> None:
    """Main function to run the bot."""
    # Set up logging
    setup_logging()
    logger.info("Starting Telemon bot...")

    # Initialize database
    try:
        await init_db()
        logger.info("Database connection established")
    except Exception as e:
        logger.error("Failed to connect to database", error=str(e))
        sys.exit(1)

    # Create bot and dispatcher
    bot = create_bot()
    dp = await create_dispatcher()

    try:
        # Get bot info
        bot_info = await bot.get_me()
        logger.info(
            "Bot started",
            username=bot_info.username,
            bot_id=bot_info.id,
        )

        # Start polling
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())

    except Exception as e:
        logger.error("Bot error", error=str(e))
        raise
    finally:
        # Cleanup
        await bot.session.close()
        await close_db()
        logger.info("Bot stopped")


def run() -> None:
    """Entry point for the application."""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    run()
