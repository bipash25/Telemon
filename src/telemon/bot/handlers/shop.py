"""Shop-related handlers."""

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from rapidfuzz import fuzz
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from telemon.database.models import InventoryItem, Item, User
from telemon.logging import get_logger

router = Router(name="shop")
logger = get_logger(__name__)

# Shop items with their prices (will be seeded to database)
SHOP_ITEMS = {
    # Evolution Stones
    "fire stone": {"id": 1, "price": 500, "category": "Evolution"},
    "water stone": {"id": 2, "price": 500, "category": "Evolution"},
    "thunder stone": {"id": 3, "price": 500, "category": "Evolution"},
    "leaf stone": {"id": 4, "price": 500, "category": "Evolution"},
    "moon stone": {"id": 5, "price": 500, "category": "Evolution"},
    "sun stone": {"id": 6, "price": 500, "category": "Evolution"},
    "dusk stone": {"id": 7, "price": 500, "category": "Evolution"},
    "dawn stone": {"id": 8, "price": 500, "category": "Evolution"},
    "shiny stone": {"id": 9, "price": 500, "category": "Evolution"},
    "ice stone": {"id": 10, "price": 500, "category": "Evolution"},
    # Battle Items
    "leftovers": {"id": 101, "price": 1000, "category": "Battle"},
    "choice band": {"id": 102, "price": 1500, "category": "Battle"},
    "choice specs": {"id": 103, "price": 1500, "category": "Battle"},
    "choice scarf": {"id": 104, "price": 1500, "category": "Battle"},
    "life orb": {"id": 105, "price": 2000, "category": "Battle"},
    "focus sash": {"id": 106, "price": 1000, "category": "Battle"},
    "assault vest": {"id": 107, "price": 1500, "category": "Battle"},
    "rocky helmet": {"id": 108, "price": 1000, "category": "Battle"},
    # Utility Items
    "rare candy": {"id": 201, "price": 200, "category": "Utility"},
    "incense": {"id": 202, "price": 500, "category": "Utility"},
    "xp boost": {"id": 203, "price": 300, "category": "Utility"},
}


SHOP_MESSAGE = """
<b>Telemon Shop</b>

<b>Evolution Items</b>
Fire Stone - 500 TC
Water Stone - 500 TC
Thunder Stone - 500 TC
Leaf Stone - 500 TC
Moon Stone - 500 TC
Sun Stone - 500 TC
Dusk Stone - 500 TC
Dawn Stone - 500 TC
Shiny Stone - 500 TC
Ice Stone - 500 TC

<b>Battle Items</b>
Leftovers - 1,000 TC
Choice Band - 1,500 TC
Choice Specs - 1,500 TC
Choice Scarf - 1,500 TC
Life Orb - 2,000 TC
Focus Sash - 1,000 TC
Assault Vest - 1,500 TC
Rocky Helmet - 1,000 TC

<b>Utility Items</b>
Rare Candy - 200 TC
Incense (1 hour) - 500 TC
XP Boost - 300 TC

<i>Use /buy &lt;item&gt; [quantity] to purchase!</i>
<i>Example: /buy fire stone 3</i>
"""


def find_item(name: str) -> tuple[str, dict] | None:
    """Find an item by name using fuzzy matching."""
    name_lower = name.lower().strip()
    
    # First try exact match
    if name_lower in SHOP_ITEMS:
        return name_lower, SHOP_ITEMS[name_lower]
    
    # Try fuzzy matching
    best_match = None
    best_score = 0
    
    for item_name, item_data in SHOP_ITEMS.items():
        score = fuzz.ratio(name_lower, item_name)
        if score > best_score and score >= 80:  # 80% match threshold
            best_score = score
            best_match = (item_name, item_data)
    
    return best_match


@router.message(Command("shop"))
async def cmd_shop(message: Message) -> None:
    """Handle /shop command."""
    await message.answer(SHOP_MESSAGE)


@router.message(Command("buy"))
async def cmd_buy(message: Message, session: AsyncSession, user: User) -> None:
    """Handle /buy command."""
    if not message.text:
        return

    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer(
            "Please specify an item to buy!\n"
            "Usage: /buy <item> [quantity]\n"
            "Example: /buy fire stone 3"
        )
        return

    # Parse item name and optional quantity
    parts = args[1].rsplit(maxsplit=1)
    
    # Try to extract quantity from the end
    quantity = 1
    item_name = args[1]
    
    if len(parts) == 2 and parts[1].isdigit():
        quantity = int(parts[1])
        item_name = parts[0]
        if quantity < 1:
            await message.answer("Quantity must be at least 1!")
            return
        if quantity > 99:
            await message.answer("Maximum quantity per purchase is 99!")
            return

    # Find the item
    match = find_item(item_name)
    if not match:
        await message.answer(
            f"Item '{item_name}' not found in the shop!\n"
            "Use /shop to see available items."
        )
        return

    item_key, item_data = match
    item_display_name = item_key.title()
    total_cost = item_data["price"] * quantity

    # Check if user has enough balance
    if user.balance < total_cost:
        await message.answer(
            f"Not enough Telecoins!\n\n"
            f"Item: {item_display_name}\n"
            f"Price: {item_data['price']:,} TC x {quantity} = {total_cost:,} TC\n"
            f"Your balance: {user.balance:,} TC\n"
            f"You need: {total_cost - user.balance:,} more TC"
        )
        return

    # Process purchase
    user.balance -= total_cost

    # Add to inventory
    item_id = item_data["id"]
    result = await session.execute(
        select(InventoryItem)
        .where(InventoryItem.user_id == user.telegram_id)
        .where(InventoryItem.item_id == item_id)
    )
    inventory_item = result.scalar_one_or_none()

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
        item=item_display_name,
        quantity=quantity,
        cost=total_cost,
    )

    await message.answer(
        f"<b>Purchase Successful!</b>\n\n"
        f"Bought: {item_display_name} x{quantity}\n"
        f"Cost: {total_cost:,} TC\n"
        f"Remaining balance: {user.balance:,} TC\n\n"
        f"<i>Use /inventory to see your items.</i>"
    )


@router.message(Command("inventory", "bag"))
async def cmd_inventory(message: Message, session: AsyncSession, user: User) -> None:
    """Handle /inventory command."""
    # Get user's inventory
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
    categories: dict[str, list[tuple[str, int]]] = {}
    
    for inv_item in inventory_items:
        # Find item info from SHOP_ITEMS
        item_name = None
        category = "Other"
        
        for name, data in SHOP_ITEMS.items():
            if data["id"] == inv_item.item_id:
                item_name = name.title()
                category = data["category"]
                break
        
        if item_name:
            if category not in categories:
                categories[category] = []
            categories[category].append((item_name, inv_item.quantity))

    # Build message
    lines = ["<b>Your Inventory</b>\n"]
    
    for category in ["Evolution", "Battle", "Utility", "Other"]:
        if category in categories:
            lines.append(f"\n<b>{category} Items</b>")
            for item_name, qty in categories[category]:
                lines.append(f"  {item_name} x{qty}")

    lines.append("\n<i>Use /use <item> [pokemon_id] to use an item.</i>")
    
    await message.answer("\n".join(lines))


@router.message(Command("use"))
async def cmd_use(message: Message, session: AsyncSession, user: User) -> None:
    """Handle /use command for using items."""
    if not message.text:
        return

    args = message.text.split(maxsplit=2)
    if len(args) < 2:
        await message.answer(
            "Please specify an item to use!\n"
            "Usage: /use <item> [pokemon_id]\n"
            "Example: /use rare candy 1"
        )
        return

    # Parse item name and optional pokemon_id
    pokemon_idx = None
    item_name = args[1] if len(args) == 2 else " ".join(args[1:])
    
    # Check if last part is a number (pokemon index)
    parts = item_name.rsplit(maxsplit=1)
    if len(parts) == 2 and parts[1].isdigit():
        pokemon_idx = int(parts[1])
        item_name = parts[0]

    # Find the item
    match = find_item(item_name)
    if not match:
        await message.answer(
            f"Item '{item_name}' not found!\n"
            "Use /inventory to see your items."
        )
        return

    item_key, item_data = match
    item_id = item_data["id"]
    item_display_name = item_key.title()

    # Check if user has this item
    result = await session.execute(
        select(InventoryItem)
        .where(InventoryItem.user_id == user.telegram_id)
        .where(InventoryItem.item_id == item_id)
        .where(InventoryItem.quantity > 0)
    )
    inventory_item = result.scalar_one_or_none()

    if not inventory_item:
        await message.answer(
            f"You don't have any {item_display_name}!\n"
            "Visit /shop to purchase items."
        )
        return

    # Handle different item types
    category = item_data["category"]
    
    if category == "Evolution":
        await message.answer(
            f"<b>Evolution Stone</b>\n\n"
            f"To use {item_display_name}, use the /evolve command:\n"
            f"<code>/evolve [pokemon_id]</code>\n\n"
            f"<i>The stone will be used automatically if the Pokemon can evolve with it.</i>"
        )
    elif item_key == "rare candy":
        # Rare candy increases level by 1
        if pokemon_idx is None:
            await message.answer(
                "Please specify which Pokemon to use the Rare Candy on!\n"
                "Usage: /use rare candy <pokemon_id>\n"
                "Example: /use rare candy 1"
            )
            return
        
        # Get the pokemon
        from telemon.database.models import Pokemon
        result = await session.execute(
            select(Pokemon)
            .where(Pokemon.owner_id == user.telegram_id)
            .order_by(Pokemon.caught_at.desc())
        )
        pokemon_list = result.scalars().all()
        
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
    elif item_key == "incense":
        await message.answer(
            "<b>Incense</b>\n\n"
            "Incense feature coming soon!\n"
            "When activated, Pokemon will spawn in your DMs for 1 hour."
        )
    elif item_key == "xp boost":
        await message.answer(
            "<b>XP Boost</b>\n\n"
            "XP Boost feature coming soon!\n"
            "When activated, you'll earn 2x XP for 1 hour."
        )
    elif category == "Battle":
        await message.answer(
            f"<b>Battle Item</b>\n\n"
            f"{item_display_name} is a held item for battle.\n"
            f"Use /give <pokemon_id> {item_key} to give it to a Pokemon."
        )
    else:
        await message.answer(
            f"Cannot use {item_display_name} directly.\n"
            f"Check /help for how to use this item."
        )
