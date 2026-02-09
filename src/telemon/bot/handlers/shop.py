"""Shop-related handlers."""

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from telemon.database.models import InventoryItem, Item, Pokemon, User
from telemon.logging import get_logger

router = Router(name="shop")
logger = get_logger(__name__)


SHOP_MESSAGE = """
<b>Telemon Shop</b>

<b>Evolution Stones</b>
<code>1</code> Fire Stone - 500 TC
<code>2</code> Water Stone - 500 TC
<code>3</code> Thunder Stone - 500 TC
<code>4</code> Leaf Stone - 500 TC
<code>5</code> Moon Stone - 500 TC
<code>6</code> Sun Stone - 500 TC
<code>7</code> Dusk Stone - 500 TC
<code>8</code> Dawn Stone - 500 TC
<code>9</code> Shiny Stone - 500 TC
<code>10</code> Ice Stone - 500 TC

<b>Battle Items</b>
<code>101</code> Leftovers - 1,000 TC
<code>102</code> Choice Band - 1,500 TC
<code>103</code> Choice Specs - 1,500 TC
<code>104</code> Choice Scarf - 1,500 TC
<code>105</code> Life Orb - 2,000 TC
<code>106</code> Focus Sash - 1,000 TC
<code>107</code> Assault Vest - 1,500 TC
<code>108</code> Rocky Helmet - 1,000 TC

<b>Utility Items</b>
<code>201</code> Rare Candy - 200 TC
<code>202</code> Incense - 500 TC
<code>203</code> XP Boost - 300 TC

<i>Use /buy &lt;id&gt; [quantity] to purchase!</i>
<i>Example: /buy 201 5 (buy 5 Rare Candies)</i>
"""


@router.message(Command("shop"))
async def cmd_shop(message: Message) -> None:
    """Handle /shop command."""
    await message.answer(SHOP_MESSAGE)


@router.message(Command("buy"))
async def cmd_buy(message: Message, session: AsyncSession, user: User) -> None:
    """Handle /buy command - buy items by ID."""
    if not message.text:
        return

    args = message.text.split()
    if len(args) < 2:
        await message.answer(
            "Please specify an item ID to buy!\n"
            "Usage: /buy [item_id] [quantity]\n"
            "Example: /buy 201 5 (buy 5 Rare Candies)\n\n"
            "Use /shop to see item IDs."
        )
        return

    # Parse item ID
    try:
        item_id = int(args[1])
    except ValueError:
        await message.answer(
            "Invalid item ID! Use a number.\n"
            "Example: /buy 201 5\n\n"
            "Use /shop to see item IDs."
        )
        return

    # Parse quantity (default 1)
    quantity = 1
    if len(args) >= 3:
        try:
            quantity = int(args[2])
            if quantity < 1:
                await message.answer("Quantity must be at least 1!")
                return
            if quantity > 99:
                await message.answer("Maximum quantity per purchase is 99!")
                return
        except ValueError:
            await message.answer("Invalid quantity! Use a number.")
            return

    # Get the item from database
    result = await session.execute(
        select(Item).where(Item.id == item_id).where(Item.is_purchasable == True)
    )
    item = result.scalar_one_or_none()

    if not item:
        await message.answer(
            f"Item with ID {item_id} not found in the shop!\n"
            "Use /shop to see available items."
        )
        return

    total_cost = item.cost * quantity

    # Check if user has enough balance
    if user.balance < total_cost:
        await message.answer(
            f"Not enough Telecoins!\n\n"
            f"Item: {item.name} (ID: {item.id})\n"
            f"Price: {item.cost:,} TC x {quantity} = {total_cost:,} TC\n"
            f"Your balance: {user.balance:,} TC\n"
            f"You need: {total_cost - user.balance:,} more TC"
        )
        return

    # Process purchase
    user.balance -= total_cost

    # Add to inventory
    inv_result = await session.execute(
        select(InventoryItem)
        .where(InventoryItem.user_id == user.telegram_id)
        .where(InventoryItem.item_id == item_id)
    )
    inventory_item = inv_result.scalar_one_or_none()

    if inventory_item:
        inventory_item.quantity += quantity
    else:
        inventory_item = InventoryItem(
            user_id=user.telegram_id,
            item_id=item_id,
            quantity=quantity,
        )
        session.add(inventory_item)

    await session.commit()

    logger.info(
        "User purchased item",
        user_id=user.telegram_id,
        item_id=item_id,
        item_name=item.name,
        quantity=quantity,
        cost=total_cost,
    )

    await message.answer(
        f"<b>Purchase Successful!</b>\n\n"
        f"Bought: {item.name} x{quantity}\n"
        f"Cost: {total_cost:,} TC\n"
        f"Remaining balance: {user.balance:,} TC\n\n"
        f"<i>Use /inventory to see your items.</i>"
    )


@router.message(Command("inventory", "bag"))
async def cmd_inventory(message: Message, session: AsyncSession, user: User) -> None:
    """Handle /inventory command."""
    # Get user's inventory with item details
    result = await session.execute(
        select(InventoryItem)
        .where(InventoryItem.user_id == user.telegram_id)
        .where(InventoryItem.quantity > 0)
    )
    inventory_items = result.scalars().all()

    if not inventory_items:
        await message.answer(
            "<b>Your Inventory</b>\n\n"
            "You don't have any items yet!\n"
            "Visit /shop to purchase items."
        )
        return

    # Group items by category
    categories: dict[str, list[tuple[int, str, int]]] = {}

    for inv_item in inventory_items:
        # Get item details
        item_result = await session.execute(
            select(Item).where(Item.id == inv_item.item_id)
        )
        item = item_result.scalar_one_or_none()

        if item:
            category = item.category.title() if item.category else "Other"
            if category not in categories:
                categories[category] = []
            categories[category].append((item.id, item.name, inv_item.quantity))

    # Build message
    lines = ["<b>Your Inventory</b>\n"]

    for category in ["Evolution", "Battle", "Utility", "Other"]:
        if category in categories:
            lines.append(f"\n<b>{category} Items</b>")
            for item_id, item_name, qty in categories[category]:
                lines.append(f"  <code>{item_id}</code> {item_name} x{qty}")

    lines.append("\n<i>Use /use [item_id] [pokemon_id] to use an item.</i>")

    await message.answer("\n".join(lines))


@router.message(Command("use"))
async def cmd_use(message: Message, session: AsyncSession, user: User) -> None:
    """Handle /use command for using items by ID."""
    if not message.text:
        return

    args = message.text.split()
    if len(args) < 2:
        await message.answer(
            "Please specify an item ID to use!\n"
            "Usage: /use [item_id] [pokemon_id]\n"
            "Example: /use 201 1 (use Rare Candy on Pokemon #1)"
        )
        return

    # Parse item ID
    try:
        item_id = int(args[1])
    except ValueError:
        await message.answer(
            "Invalid item ID! Use a number.\n"
            "Use /inventory to see your items."
        )
        return

    # Parse optional pokemon index
    pokemon_idx = None
    if len(args) >= 3:
        try:
            pokemon_idx = int(args[2])
        except ValueError:
            await message.answer("Invalid Pokemon ID! Use a number.")
            return

    # Check if user has this item
    inv_result = await session.execute(
        select(InventoryItem)
        .where(InventoryItem.user_id == user.telegram_id)
        .where(InventoryItem.item_id == item_id)
        .where(InventoryItem.quantity > 0)
    )
    inventory_item = inv_result.scalar_one_or_none()

    if not inventory_item:
        await message.answer(
            f"You don't have item ID {item_id}!\n"
            "Use /inventory to see your items."
        )
        return

    # Get item details
    item_result = await session.execute(
        select(Item).where(Item.id == item_id)
    )
    item = item_result.scalar_one_or_none()

    if not item:
        await message.answer("Item not found!")
        return

    # Handle different item types based on category
    category = item.category.lower() if item.category else ""

    if category == "evolution":
        await message.answer(
            f"<b>Evolution Stone</b>\n\n"
            f"To use {item.name}, use the /evolve command:\n"
            f"<code>/evolve [pokemon_id]</code>\n\n"
            f"<i>The stone will be used automatically if the Pokemon can evolve with it.</i>"
        )
    elif item_id == 201:  # Rare Candy
        if pokemon_idx is None:
            await message.answer(
                "Please specify which Pokemon to use the Rare Candy on!\n"
                "Usage: /use 201 [pokemon_id]\n"
                "Example: /use 201 1"
            )
            return

        # Get the pokemon
        poke_result = await session.execute(
            select(Pokemon)
            .where(Pokemon.owner_id == user.telegram_id)
            .order_by(Pokemon.caught_at.desc())
        )
        pokemon_list = poke_result.scalars().all()

        if pokemon_idx < 1 or pokemon_idx > len(pokemon_list):
            await message.answer(f"Invalid Pokemon ID! You have {len(pokemon_list)} Pokemon.")
            return

        pokemon = pokemon_list[pokemon_idx - 1]

        if pokemon.level >= 100:
            await message.answer(f"{pokemon.species.name} is already at max level!")
            return

        # Use the rare candy
        pokemon.level += 1
        inventory_item.quantity -= 1
        await session.commit()

        await message.answer(
            f"<b>Rare Candy Used!</b>\n\n"
            f"{pokemon.nickname or pokemon.species.name} grew to Lv.{pokemon.level}!\n\n"
            f"<i>Rare Candies remaining: {inventory_item.quantity}</i>"
        )

        logger.info(
            "User used rare candy",
            user_id=user.telegram_id,
            pokemon=pokemon.species.name,
            new_level=pokemon.level,
        )
    elif item_id == 202:  # Incense
        await message.answer(
            "<b>Incense</b>\n\n"
            "Incense feature coming soon!\n"
            "When activated, Pokemon will spawn in your DMs for 1 hour."
        )
    elif item_id == 203:  # XP Boost
        await message.answer(
            "<b>XP Boost</b>\n\n"
            "XP Boost feature coming soon!\n"
            "When activated, you'll earn 2x XP for 1 hour."
        )
    elif category == "battle":
        await message.answer(
            f"<b>Battle Item</b>\n\n"
            f"{item.name} is a held item for battle.\n"
            f"Use /give [pokemon_id] [item_id] to give it to a Pokemon."
        )
    else:
        await message.answer(
            f"Cannot use {item.name} directly.\n"
            f"Check /help for how to use this item."
        )
