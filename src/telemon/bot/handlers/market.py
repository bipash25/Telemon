"""Market-related handlers for Pokemon marketplace."""

import math
from datetime import datetime, timedelta

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from telemon.database.models import (
    ListingStatus,
    MarketListing,
    Pokemon,
    PokemonSpecies,
    User,
)
from telemon.logging import get_logger

router = Router(name="market")
logger = get_logger(__name__)

# Constants
LISTINGS_PER_PAGE = 5
DEFAULT_LISTING_DAYS = 7  # Listings expire after 7 days
MIN_PRICE = 100
MAX_PRICE = 1_000_000_000  # 1 billion TC max


async def get_user_pokemon_list(session: AsyncSession, user_id: int) -> list[Pokemon]:
    """Get all Pokemon for a user ordered by catch time."""
    result = await session.execute(
        select(Pokemon)
        .where(Pokemon.owner_id == user_id)
        .order_by(Pokemon.caught_at.desc())
    )
    return list(result.scalars().all())


async def get_active_listings(
    session: AsyncSession,
    page: int = 1,
    search_name: str | None = None,
    search_type: str | None = None,
    min_level: int | None = None,
    max_level: int | None = None,
    shiny_only: bool = False,
) -> tuple[list[MarketListing], int]:
    """Get active market listings with pagination and filters."""
    # Base query
    query = (
        select(MarketListing)
        .where(MarketListing.status == ListingStatus.ACTIVE)
        .where(MarketListing.expires_at > datetime.utcnow())
    )

    # Build count query
    count_query = (
        select(func.count(MarketListing.id))
        .where(MarketListing.status == ListingStatus.ACTIVE)
        .where(MarketListing.expires_at > datetime.utcnow())
    )

    # Apply filters via subqueries if needed
    if search_name or search_type or min_level or max_level or shiny_only:
        # Get Pokemon IDs that match filters
        pokemon_query = select(Pokemon.id)

        if search_name:
            # Join with species to filter by name
            pokemon_query = pokemon_query.join(PokemonSpecies)
            pokemon_query = pokemon_query.where(
                PokemonSpecies.name.ilike(f"%{search_name}%")
            )

        if min_level:
            pokemon_query = pokemon_query.where(Pokemon.level >= min_level)

        if max_level:
            pokemon_query = pokemon_query.where(Pokemon.level <= max_level)

        if shiny_only:
            pokemon_query = pokemon_query.where(Pokemon.is_shiny == True)

        query = query.where(MarketListing.pokemon_id.in_(pokemon_query))
        count_query = count_query.where(MarketListing.pokemon_id.in_(pokemon_query))

    # Get total count
    count_result = await session.execute(count_query)
    total_count = count_result.scalar() or 0

    # Apply pagination and ordering
    offset = (page - 1) * LISTINGS_PER_PAGE
    query = (
        query
        .order_by(MarketListing.listed_at.desc())
        .offset(offset)
        .limit(LISTINGS_PER_PAGE)
    )

    result = await session.execute(query)
    listings = list(result.scalars().all())

    return listings, total_count


async def get_user_listings(
    session: AsyncSession, user_id: int
) -> list[MarketListing]:
    """Get active listings for a user."""
    result = await session.execute(
        select(MarketListing)
        .where(MarketListing.seller_id == user_id)
        .where(MarketListing.status == ListingStatus.ACTIVE)
        .order_by(MarketListing.listed_at.desc())
    )
    return list(result.scalars().all())


async def format_listing(
    session: AsyncSession, listing: MarketListing, index: int | None = None
) -> str:
    """Format a single listing for display."""
    # Get Pokemon details
    result = await session.execute(
        select(Pokemon).where(Pokemon.id == listing.pokemon_id)
    )
    pokemon = result.scalar_one_or_none()

    if not pokemon:
        return f"#{index or '?'} - [Pokemon not found]"

    # Get seller info
    seller_result = await session.execute(
        select(User).where(User.telegram_id == listing.seller_id)
    )
    seller = seller_result.scalar_one_or_none()
    seller_name = seller.display_name if seller else f"User {listing.seller_id}"

    shiny = " ✨" if pokemon.is_shiny else ""
    iv_pct = pokemon.iv_percentage

    # Time remaining
    time_left = listing.expires_at - datetime.utcnow()
    if time_left.days > 0:
        time_str = f"{time_left.days}d"
    elif time_left.seconds > 3600:
        time_str = f"{time_left.seconds // 3600}h"
    else:
        time_str = f"{time_left.seconds // 60}m"

    prefix = f"<b>#{index}</b> " if index else ""

    return (
        f"{prefix}<b>{pokemon.species.name}</b>{shiny} Lv.{pokemon.level}\n"
        f"   IV: {iv_pct:.1f}% | Price: {listing.price:,} TC\n"
        f"   Seller: {seller_name} | Expires: {time_str}"
    )


def build_market_keyboard(
    page: int, total_pages: int, search_params: str = ""
) -> InlineKeyboardBuilder:
    """Build pagination keyboard for market."""
    builder = InlineKeyboardBuilder()

    if total_pages > 1:
        buttons = []

        if page > 1:
            buttons.append(("◀️ Prev", f"market:page:{page - 1}:{search_params}"))

        buttons.append((f"{page}/{total_pages}", "market:noop"))

        if page < total_pages:
            buttons.append(("Next ▶️", f"market:page:{page + 1}:{search_params}"))

        for text, callback_data in buttons:
            builder.button(text=text, callback_data=callback_data)

        builder.adjust(3)

    return builder


@router.message(Command("market"))
async def cmd_market(message: Message, session: AsyncSession, user: User) -> None:
    """Handle /market command and subcommands."""
    text = message.text or ""
    args = text.split()

    if len(args) < 2:
        # Show market browse
        await show_market(message, session, page=1)
        return

    subcommand = args[1].lower()

    if subcommand == "sell":
        await market_sell(message, session, user, args[2:])
    elif subcommand == "buy":
        await market_buy(message, session, user, args[2:])
    elif subcommand == "cancel":
        await market_cancel(message, session, user, args[2:])
    elif subcommand == "listings" or subcommand == "my":
        await market_my_listings(message, session, user)
    elif subcommand == "search":
        await market_search(message, session, args[2:])
    elif subcommand == "info":
        await market_info(message, session, args[2:])
    else:
        # Maybe it's a page number
        if subcommand.isdigit():
            await show_market(message, session, page=int(subcommand))
        else:
            await message.answer(
                "❓ Unknown market command.\n\n"
                "<b>Usage:</b>\n"
                "/market - Browse listings\n"
                "/market sell [pokemon_id] [price] - List for sale\n"
                "/market buy [listing_#] - Purchase listing\n"
                "/market cancel [listing_#] - Cancel your listing\n"
                "/market listings - View your listings\n"
                "/market search [name] - Search by Pokemon name\n"
                "/market info [listing_#] - View listing details"
            )


async def show_market(
    message: Message,
    session: AsyncSession,
    page: int = 1,
    search_name: str | None = None,
) -> None:
    """Show market listings with pagination."""
    listings, total_count = await get_active_listings(
        session, page=page, search_name=search_name
    )

    if not listings and page == 1:
        search_note = f' for "{search_name}"' if search_name else ""
        await message.answer(
            f"🏪 <b>Global Marketplace</b>\n\n"
            f"No listings found{search_note}.\n\n"
            f"<i>Be the first to list a Pokemon!</i>\n"
            f"Use: /market sell [pokemon_id] [price]"
        )
        return

    total_pages = math.ceil(total_count / LISTINGS_PER_PAGE)

    # Format listings
    lines = ["🏪 <b>Global Marketplace</b>\n"]

    if search_name:
        lines.append(f"🔍 Searching: {search_name}\n")

    lines.append(f"<i>Showing {len(listings)} of {total_count} listings</i>\n")

    # Number listings globally based on page
    start_index = (page - 1) * LISTINGS_PER_PAGE + 1
    for i, listing in enumerate(listings):
        listing_text = await format_listing(session, listing, index=start_index + i)
        lines.append(f"\n{listing_text}")

    lines.append("\n\n<b>Commands:</b>")
    lines.append("/market buy [#] - Purchase listing")
    lines.append("/market info [#] - View details")
    lines.append("/market sell [id] [price] - List your Pokemon")

    keyboard = build_market_keyboard(page, total_pages, search_name or "")

    await message.answer("\n".join(lines), reply_markup=keyboard.as_markup())


async def market_sell(
    message: Message, session: AsyncSession, user: User, args: list
) -> None:
    """List a Pokemon for sale on the market."""
    if len(args) < 2:
        await message.answer(
            "📝 <b>Sell Pokemon</b>\n\n"
            "Usage: /market sell [pokemon_id] [price]\n\n"
            "Example: /market sell 5 10000\n"
            "(Lists your 5th Pokemon for 10,000 TC)\n\n"
            f"Min price: {MIN_PRICE:,} TC\n"
            f"Max price: {MAX_PRICE:,} TC\n"
            f"Listings expire after {DEFAULT_LISTING_DAYS} days"
        )
        return

    # Parse Pokemon ID
    try:
        pokemon_idx = int(args[0])
    except ValueError:
        await message.answer("❌ Invalid Pokemon ID. Use a number.")
        return

    # Parse price
    try:
        price = int(args[1].replace(",", "").replace("k", "000").replace("m", "000000"))
    except ValueError:
        await message.answer("❌ Invalid price. Use a number (supports k/m suffix).")
        return

    if price < MIN_PRICE:
        await message.answer(f"❌ Minimum price is {MIN_PRICE:,} TC.")
        return

    if price > MAX_PRICE:
        await message.answer(f"❌ Maximum price is {MAX_PRICE:,} TC.")
        return

    # Get user's Pokemon
    pokemon_list = await get_user_pokemon_list(session, user.telegram_id)

    if not pokemon_list:
        await message.answer("❌ You don't have any Pokemon!")
        return

    if pokemon_idx < 1 or pokemon_idx > len(pokemon_list):
        await message.answer(
            f"❌ Invalid Pokemon ID! You have {len(pokemon_list)} Pokemon.\n"
            "Use /pokemon to see your collection."
        )
        return

    pokemon = pokemon_list[pokemon_idx - 1]

    # Check if Pokemon can be listed
    if pokemon.is_on_market:
        await message.answer(f"❌ {pokemon.species.name} is already on the market!")
        return

    if pokemon.is_in_trade:
        await message.answer(f"❌ {pokemon.species.name} is in an active trade!")
        return

    if pokemon.is_favorite:
        await message.answer(
            f"❌ {pokemon.species.name} is favorited!\n"
            "Unfavorite it first to sell."
        )
        return

    # Check if user's selected Pokemon
    if str(pokemon.id) == user.selected_pokemon_id:
        await message.answer(
            f"❌ {pokemon.species.name} is your selected Pokemon!\n"
            "Select a different Pokemon first with /select"
        )
        return

    # Create listing
    expires_at = datetime.utcnow() + timedelta(days=DEFAULT_LISTING_DAYS)

    listing = MarketListing(
        seller_id=user.telegram_id,
        pokemon_id=pokemon.id,
        price=price,
        status=ListingStatus.ACTIVE,
        expires_at=expires_at,
    )
    session.add(listing)

    # Mark Pokemon as on market
    pokemon.is_on_market = True

    await session.commit()

    logger.info(
        "Market listing created",
        listing_id=str(listing.id),
        seller_id=user.telegram_id,
        pokemon_id=str(pokemon.id),
        pokemon_name=pokemon.species.name,
        price=price,
    )

    shiny = " ✨" if pokemon.is_shiny else ""
    await message.answer(
        f"✅ <b>Listed on Market!</b>\n\n"
        f"Pokemon: <b>{pokemon.species.name}</b>{shiny} Lv.{pokemon.level}\n"
        f"IV: {pokemon.iv_percentage:.1f}%\n"
        f"Price: {price:,} TC\n"
        f"Expires: {DEFAULT_LISTING_DAYS} days\n\n"
        f"<i>Your Pokemon is now visible to all trainers!</i>"
    )


async def market_buy(
    message: Message, session: AsyncSession, user: User, args: list
) -> None:
    """Buy a Pokemon from the market."""
    if not args:
        await message.answer(
            "🛒 <b>Buy Pokemon</b>\n\n"
            "Usage: /market buy [listing_#]\n\n"
            "Example: /market buy 3\n"
            "(Buys listing #3 from the market)\n\n"
            "Use /market to browse listings first."
        )
        return

    # Parse listing number
    try:
        listing_num = int(args[0])
    except ValueError:
        await message.answer("❌ Invalid listing number.")
        return

    if listing_num < 1:
        await message.answer("❌ Listing number must be positive.")
        return

    # Get the listing by index (we need to fetch all active listings and find by index)
    # This is a bit inefficient but maintains consistency with display order
    offset = listing_num - 1
    result = await session.execute(
        select(MarketListing)
        .where(MarketListing.status == ListingStatus.ACTIVE)
        .where(MarketListing.expires_at > datetime.utcnow())
        .order_by(MarketListing.listed_at.desc())
        .offset(offset)
        .limit(1)
    )
    listing = result.scalar_one_or_none()

    if not listing:
        await message.answer(
            f"❌ Listing #{listing_num} not found.\n"
            "Use /market to see available listings."
        )
        return

    # Check if user is buying their own listing
    if listing.seller_id == user.telegram_id:
        await message.answer("❌ You can't buy your own listing!")
        return

    # Check user balance
    if user.balance < listing.price:
        await message.answer(
            f"❌ Not enough Telecoins!\n\n"
            f"Price: {listing.price:,} TC\n"
            f"Your balance: {user.balance:,} TC\n"
            f"Need: {listing.price - user.balance:,} TC more"
        )
        return

    # Get Pokemon
    result = await session.execute(
        select(Pokemon).where(Pokemon.id == listing.pokemon_id)
    )
    pokemon = result.scalar_one_or_none()

    if not pokemon:
        await message.answer("❌ Pokemon not found. Listing may be corrupted.")
        return

    # Get seller
    result = await session.execute(
        select(User).where(User.telegram_id == listing.seller_id)
    )
    seller = result.scalar_one_or_none()

    if not seller:
        await message.answer("❌ Seller not found.")
        return

    # Execute purchase
    # Transfer coins
    user.balance -= listing.price
    seller.balance += listing.price

    # Transfer Pokemon
    pokemon.owner_id = user.telegram_id
    pokemon.is_on_market = False

    # Update listing
    listing.status = ListingStatus.SOLD
    listing.buyer_id = user.telegram_id
    listing.sold_at = datetime.utcnow()

    await session.commit()

    logger.info(
        "Market purchase completed",
        listing_id=str(listing.id),
        buyer_id=user.telegram_id,
        seller_id=seller.telegram_id,
        pokemon_id=str(pokemon.id),
        pokemon_name=pokemon.species.name,
        price=listing.price,
    )

    shiny = " ✨" if pokemon.is_shiny else ""
    await message.answer(
        f"🎉 <b>Purchase Complete!</b>\n\n"
        f"You bought <b>{pokemon.species.name}</b>{shiny} Lv.{pokemon.level}\n"
        f"IV: {pokemon.iv_percentage:.1f}%\n"
        f"Price: {listing.price:,} TC\n\n"
        f"Seller: {seller.display_name}\n"
        f"Your new balance: {user.balance:,} TC\n\n"
        f"<i>Use /pokemon to see your new Pokemon!</i>"
    )


async def market_cancel(
    message: Message, session: AsyncSession, user: User, args: list
) -> None:
    """Cancel a user's market listing."""
    if not args:
        await message.answer(
            "❌ <b>Cancel Listing</b>\n\n"
            "Usage: /market cancel [listing_#]\n\n"
            "Use /market listings to see your active listings."
        )
        return

    # Parse listing number (from user's listings)
    try:
        listing_num = int(args[0])
    except ValueError:
        await message.answer("❌ Invalid listing number.")
        return

    # Get user's listings
    user_listings = await get_user_listings(session, user.telegram_id)

    if not user_listings:
        await message.answer("❌ You don't have any active listings.")
        return

    if listing_num < 1 or listing_num > len(user_listings):
        await message.answer(
            f"❌ Invalid listing number. You have {len(user_listings)} active listings.\n"
            "Use /market listings to see them."
        )
        return

    listing = user_listings[listing_num - 1]

    # Get Pokemon
    result = await session.execute(
        select(Pokemon).where(Pokemon.id == listing.pokemon_id)
    )
    pokemon = result.scalar_one_or_none()

    if not pokemon:
        await message.answer("❌ Pokemon not found.")
        return

    # Cancel listing
    listing.status = ListingStatus.CANCELLED
    pokemon.is_on_market = False

    await session.commit()

    logger.info(
        "Market listing cancelled",
        listing_id=str(listing.id),
        seller_id=user.telegram_id,
        pokemon_id=str(pokemon.id),
    )

    await message.answer(
        f"✅ <b>Listing Cancelled</b>\n\n"
        f"<b>{pokemon.species.name}</b> has been removed from the market.\n"
        f"It's back in your collection!"
    )


async def market_my_listings(
    message: Message, session: AsyncSession, user: User
) -> None:
    """Show user's active listings."""
    listings = await get_user_listings(session, user.telegram_id)

    if not listings:
        await message.answer(
            "📋 <b>Your Listings</b>\n\n"
            "You don't have any active listings.\n\n"
            "Use /market sell [pokemon_id] [price] to list a Pokemon!"
        )
        return

    lines = [
        "📋 <b>Your Active Listings</b>\n",
        f"<i>You have {len(listings)} active listing(s)</i>\n",
    ]

    for i, listing in enumerate(listings, 1):
        # Get Pokemon
        result = await session.execute(
            select(Pokemon).where(Pokemon.id == listing.pokemon_id)
        )
        pokemon = result.scalar_one_or_none()

        if not pokemon:
            continue

        shiny = " ✨" if pokemon.is_shiny else ""
        time_left = listing.expires_at - datetime.utcnow()
        if time_left.days > 0:
            time_str = f"{time_left.days}d remaining"
        elif time_left.seconds > 3600:
            time_str = f"{time_left.seconds // 3600}h remaining"
        else:
            time_str = f"{time_left.seconds // 60}m remaining"

        lines.append(
            f"\n<b>#{i}</b> {pokemon.species.name}{shiny} Lv.{pokemon.level}\n"
            f"   IV: {pokemon.iv_percentage:.1f}% | Price: {listing.price:,} TC\n"
            f"   Views: {listing.view_count} | {time_str}"
        )

    lines.append("\n\n<b>Commands:</b>")
    lines.append("/market cancel [#] - Remove listing")

    await message.answer("\n".join(lines))


async def market_search(
    message: Message, session: AsyncSession, args: list
) -> None:
    """Search market by Pokemon name."""
    if not args:
        await message.answer(
            "🔍 <b>Search Market</b>\n\n"
            "Usage: /market search [name]\n\n"
            "Example: /market search pikachu\n"
            "(Shows all Pikachu listings)"
        )
        return

    search_name = " ".join(args)
    await show_market(message, session, page=1, search_name=search_name)


async def market_info(
    message: Message, session: AsyncSession, args: list
) -> None:
    """Show detailed info about a listing."""
    if not args:
        await message.answer(
            "ℹ️ <b>Listing Info</b>\n\n"
            "Usage: /market info [listing_#]\n\n"
            "Example: /market info 3\n"
            "(Shows details for listing #3)"
        )
        return

    # Parse listing number
    try:
        listing_num = int(args[0])
    except ValueError:
        await message.answer("❌ Invalid listing number.")
        return

    # Get listing
    offset = listing_num - 1
    result = await session.execute(
        select(MarketListing)
        .where(MarketListing.status == ListingStatus.ACTIVE)
        .where(MarketListing.expires_at > datetime.utcnow())
        .order_by(MarketListing.listed_at.desc())
        .offset(offset)
        .limit(1)
    )
    listing = result.scalar_one_or_none()

    if not listing:
        await message.answer(f"❌ Listing #{listing_num} not found.")
        return

    # Increment view count
    listing.view_count += 1
    await session.commit()

    # Get Pokemon details
    result = await session.execute(
        select(Pokemon).where(Pokemon.id == listing.pokemon_id)
    )
    pokemon = result.scalar_one_or_none()

    if not pokemon:
        await message.answer("❌ Pokemon not found.")
        return

    # Get seller
    result = await session.execute(
        select(User).where(User.telegram_id == listing.seller_id)
    )
    seller = result.scalar_one_or_none()

    shiny = " ✨" if pokemon.is_shiny else ""
    time_left = listing.expires_at - datetime.utcnow()
    if time_left.days > 0:
        time_str = f"{time_left.days} days"
    elif time_left.seconds > 3600:
        time_str = f"{time_left.seconds // 3600} hours"
    else:
        time_str = f"{time_left.seconds // 60} minutes"

    # Format IVs
    iv_line = (
        f"HP: {pokemon.iv_hp} | ATK: {pokemon.iv_attack} | DEF: {pokemon.iv_defense}\n"
        f"SpA: {pokemon.iv_sp_attack} | SpD: {pokemon.iv_sp_defense} | SPE: {pokemon.iv_speed}"
    )

    await message.answer(
        f"ℹ️ <b>Listing #{listing_num} Details</b>\n\n"
        f"<b>{pokemon.species.name}</b>{shiny}\n"
        f"Level: {pokemon.level}\n"
        f"Nature: {pokemon.nature.title()}\n"
        f"Gender: {pokemon.gender or 'Unknown'}\n\n"
        f"<b>IVs ({pokemon.iv_percentage:.1f}%)</b>\n"
        f"{iv_line}\n\n"
        f"<b>Price:</b> {listing.price:,} TC\n"
        f"<b>Seller:</b> {seller.display_name if seller else 'Unknown'}\n"
        f"<b>Views:</b> {listing.view_count}\n"
        f"<b>Expires in:</b> {time_str}\n\n"
        f"<i>Use /market buy {listing_num} to purchase</i>"
    )


@router.callback_query(F.data.startswith("market:"))
async def handle_market_callback(
    callback: CallbackQuery, session: AsyncSession
) -> None:
    """Handle market pagination callbacks."""
    data = callback.data.split(":")

    if len(data) < 2:
        await callback.answer("Invalid callback")
        return

    action = data[1]

    if action == "noop":
        await callback.answer()
        return

    if action == "page":
        page = int(data[2]) if len(data) > 2 else 1
        search_name = data[3] if len(data) > 3 and data[3] else None

        listings, total_count = await get_active_listings(
            session, page=page, search_name=search_name
        )

        if not listings:
            await callback.answer("No listings on this page")
            return

        total_pages = math.ceil(total_count / LISTINGS_PER_PAGE)

        # Format listings
        lines = ["🏪 <b>Global Marketplace</b>\n"]

        if search_name:
            lines.append(f"🔍 Searching: {search_name}\n")

        lines.append(f"<i>Showing {len(listings)} of {total_count} listings</i>\n")

        start_index = (page - 1) * LISTINGS_PER_PAGE + 1
        for i, listing in enumerate(listings):
            listing_text = await format_listing(session, listing, index=start_index + i)
            lines.append(f"\n{listing_text}")

        lines.append("\n\n<b>Commands:</b>")
        lines.append("/market buy [#] - Purchase listing")
        lines.append("/market info [#] - View details")

        keyboard = build_market_keyboard(page, total_pages, search_name or "")

        await callback.message.edit_text(
            "\n".join(lines), reply_markup=keyboard.as_markup()
        )
        await callback.answer()
