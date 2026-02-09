"""Handler registration."""

from aiogram import Dispatcher

from telemon.bot.handlers import (
    admin,
    battle,
    catch,
    help_cmd,
    market,
    pokedex,
    pokemon,
    profile,
    shinyhunt,
    shop,
    spawn,
    start,
    trade,
)


def register_all_handlers(dp: Dispatcher) -> None:
    """Register all handlers with the dispatcher."""
    # Core handlers
    dp.include_router(start.router)
    dp.include_router(help_cmd.router)
    dp.include_router(profile.router)

    # Pokemon handlers
    dp.include_router(catch.router)
    dp.include_router(pokemon.router)
    dp.include_router(pokedex.router)
    dp.include_router(shinyhunt.router)

    # Battle handlers
    dp.include_router(battle.router)

    # Economy handlers
    dp.include_router(trade.router)
    dp.include_router(market.router)
    dp.include_router(shop.router)

    # Admin handlers
    dp.include_router(admin.router)

    # Spawn handler (MUST be last - catches all group messages)
    dp.include_router(spawn.router)


__all__ = ["register_all_handlers"]
