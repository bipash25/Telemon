"""Main entry point for Telemon bot."""

import asyncio
import sys

from telemon.bot import create_bot, create_dispatcher
from telemon.database import close_db, init_db
from telemon.logging import get_logger, setup_logging

logger = get_logger(__name__)


async def timed_spawn_loop(bot) -> None:
    """Background task: periodically spawn Pokemon in active groups.

    Every 10 minutes, check groups that haven't had a spawn in 4-6 hours
    and have spawn_enabled. Force a spawn if there's no active spawn.
    """
    from datetime import datetime, timedelta
    from sqlalchemy import select
    from telemon.database import async_session_factory
    from telemon.database.models import Group
    from telemon.core.spawning import create_spawn, get_random_species, get_active_spawn

    await asyncio.sleep(60)  # Wait 1 minute after startup

    while True:
        try:
            async with async_session_factory() as session:
                # Find groups that are active, spawn-enabled, and haven't
                # had a spawn in 4+ hours
                cutoff = datetime.utcnow() - timedelta(hours=4)
                result = await session.execute(
                    select(Group)
                    .where(Group.spawn_enabled == True)
                    .where(
                        (Group.last_spawn_at < cutoff) |
                        (Group.last_spawn_at.is_(None))
                    )
                )
                groups = result.scalars().all()

                for group in groups:
                    # Skip if there's already an active spawn
                    active = await get_active_spawn(session, group.chat_id)
                    if active:
                        continue

                    # Only spawn in groups that have had at least some activity
                    if group.total_spawns == 0 and group.message_count < 5:
                        continue

                    species = await get_random_species(session)
                    if not species:
                        continue

                    spawn = await create_spawn(
                        session=session,
                        chat_id=group.chat_id,
                        message_id=0,
                        species=species,
                    )

                    if spawn:
                        from telemon.bot.handlers.spawn import send_spawn_message
                        msg_id = await send_spawn_message(bot, group.chat_id, spawn)
                        if msg_id:
                            spawn.message_id = msg_id
                            await session.commit()
                            logger.info(
                                "Timed spawn triggered",
                                chat_id=group.chat_id,
                                species=species.name,
                            )

        except Exception as e:
            logger.error("Error in timed spawn loop", error=str(e))

        # Check every 10 minutes
        await asyncio.sleep(600)


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

        # Start timed spawn background task
        spawn_task = asyncio.create_task(timed_spawn_loop(bot))

        # Start polling
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())

    except Exception as e:
        logger.error("Bot error", error=str(e))
        raise
    finally:
        # Cleanup
        spawn_task.cancel()
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
