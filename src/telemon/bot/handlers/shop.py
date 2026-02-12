"""Shop, inventory, and item usage handlers."""

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from telemon.core.evolution import check_evolution, evolve_pokemon, get_possible_evolutions
from telemon.core.items import (
    ALL_ITEMS,
    ITEM_BY_ID,
    ITEM_BY_NAME,
    LINKING_CORD_ID,
    RARE_CANDY_ID,
    SOOTHE_BELL_ID,
)
from telemon.database.models import InventoryItem, Item, Pokemon, User
from telemon.logging import get_logger

router = Router(name="shop")
logger = get_logger(__name__)

# Friendship gain from /pet
PET_FRIENDSHIP_GAIN = 5
SOOTHE_BELL_MULTIPLIER = 2

# ──────────────────────────────────────────────
# Shop category data (inline keyboard navigation)
# ──────────────────────────────────────────────

SHOP_CATEGORIES: dict[str, dict] = {
    "evo_stones": {
        "emoji": "🪨",
        "title": "Evo Stones",
        "items": [i for i in ALL_ITEMS if i["category"] == "evolution" and i["id"] <= 10],
    },
    "evo_items": {
        "emoji": "🔗",
        "title": "Evo Items",
        "items": [i for i in ALL_ITEMS if i["category"] == "evolution" and 11 <= i["id"] <= 29],
    },
    "battle": {
        "emoji": "⚔️",
        "title": "Battle",
        "items": [i for i in ALL_ITEMS if i["category"] == "battle"],
    },
    "mega": {
        "emoji": "🌀",
        "title": "Mega Stones",
        "items": [i for i in ALL_ITEMS if i["category"] == "mega_stone"],
    },
    "utility": {
        "emoji": "🧪",
        "title": "Utility",
        "items": [i for i in ALL_ITEMS if i["category"] == "utility"],
    },
    "special": {
        "emoji": "✨",
        "title": "Special",
        "items": [i for i in ALL_ITEMS if i["category"] == "special"],
    },
}

SHOP_CATEGORY_ORDER = ["evo_stones", "evo_items", "battle", "mega", "utility", "special"]

SHOP_OVERVIEW = (
    "<b>Telemon Shop</b>\n\n"
    "Tap a category to browse items.\n\n"
    "<i>Use /buy [id] [qty] to purchase.\n"
    "Use /shopinfo [id] for item details.</i>"
)


def _build_shop_keyboard() -> InlineKeyboardBuilder:
    """Build the shop category selection keyboard."""
    builder = InlineKeyboardBuilder()
    for key in SHOP_CATEGORY_ORDER:
        cat = SHOP_CATEGORIES[key]
        count = len(cat["items"])
        builder.button(
            text=f"{cat['emoji']} {cat['title']} ({count})",
            callback_data=f"shop:{key}",
        )
    builder.adjust(2)
    return builder


def _shop_back_keyboard() -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    builder.button(text="◀️ Back to shop", callback_data="shop:back")
    return builder


def _build_category_text(key: str) -> str:
    """Build the item list text for a shop category."""
    cat = SHOP_CATEGORIES[key]
    lines = [f"<b>{cat['emoji']} {cat['title']}</b>\n"]
    for item in cat["items"]:
        lines.append(f"  <code>{item['id']}</code> {item['name']} — {item['cost']:,} TC")
    lines.append(f"\n<i>/buy [id] [qty] to purchase.  /shopinfo [id] for details.</i>")
    return "\n".join(lines)


@router.message(Command("shop"))
async def cmd_shop(message: Message) -> None:
    """Handle /shop command."""
    keyboard = _build_shop_keyboard()
    await message.answer(SHOP_OVERVIEW, reply_markup=keyboard.as_markup())


@router.callback_query(F.data.startswith("shop:"))
async def callback_shop(callback: CallbackQuery) -> None:
    """Handle shop category selection."""
    data = (callback.data or "").split(":", 1)
    if len(data) < 2:
        await callback.answer()
        return

    key = data[1]

    if key == "back":
        keyboard = _build_shop_keyboard()
        await callback.message.edit_text(
            SHOP_OVERVIEW, reply_markup=keyboard.as_markup()
        )
        await callback.answer()
        return

    cat = SHOP_CATEGORIES.get(key)
    if not cat:
        await callback.answer("Unknown category")
        return

    text = _build_category_text(key)
    await callback.message.edit_text(
        text, reply_markup=_shop_back_keyboard().as_markup()
    )
    await callback.answer()


@router.message(Command("shopinfo", "iteminfo"))
async def cmd_shopinfo(message: Message) -> None:
    """Show detailed info about a shop item."""
    text = message.text or ""
    args = text.split()

    if len(args) < 2:
        await message.answer("Usage: /shopinfo [item_id]\nExample: /shopinfo 29")
        return

    try:
        item_id = int(args[1])
    except ValueError:
        # Try by name
        name = " ".join(args[1:]).lower()
        item_data = ITEM_BY_NAME.get(name)
        if not item_data:
            await message.answer("Item not found! Use /shop to see item IDs.")
            return
        item_id = item_data["id"]

    item_data = ITEM_BY_ID.get(item_id)
    if not item_data:
        await message.answer("Item not found! Use /shop to see item IDs.")
        return

    desc = item_data.get("description", "No description available.")
    props = []
    if item_data.get("is_consumable"):
        props.append("Consumable")
    if item_data.get("is_holdable"):
        props.append("Holdable")

    await message.answer(
        f"<b>{item_data['name']}</b> (ID: {item_data['id']})\n\n"
        f"{desc}\n\n"
        f"<b>Category:</b> {item_data['category'].title()}\n"
        f"<b>Cost:</b> {item_data['cost']:,} TC\n"
        f"<b>Sell:</b> {item_data['sell_price']:,} TC\n"
        f"<b>Properties:</b> {', '.join(props) if props else 'None'}"
    )


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

    # Display order with clean names
    category_display = [
        ("Evolution", "Evolution"),
        ("Battle", "Battle"),
        ("Mega_Stone", "Mega Stone"),
        ("Utility", "Utility"),
        ("Special", "Special"),
        ("Other", "Other"),
    ]
    for cat_key, cat_label in category_display:
        if cat_key in categories:
            lines.append(f"\n<b>{cat_label} Items</b>")
            for item_id, item_name, qty in categories[cat_key]:
                lines.append(f"  <code>{item_id}</code> {item_name} x{qty}")

    lines.append("\n<i>Use /use [item_id] [pokemon#] to use an item.</i>")

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
            "Usage: /use [item_id] [pokemon#]\n"
            "Example: /use 201 1 (use Rare Candy on Pokemon #1)\n"
            "Example: /use 29 (use Linking Cord on selected Pokemon)"
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
            await message.answer("Invalid Pokemon number! Use a number.")
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

    category = item.category.lower() if item.category else ""

    # ── Evolution items: direct use triggers evolution ──
    if category == "evolution":
        # Get the target Pokemon
        poke = await _resolve_use_target(session, user, pokemon_idx)
        if poke is None:
            await message.answer(
                f"Please specify which Pokemon to use {item.name} on!\n"
                f"Usage: /use {item_id} [pokemon#]\n"
                f"Or select a Pokemon first with /select [number]"
            )
            return

        # Is this a Linking Cord?
        if item_id == LINKING_CORD_ID:
            # Try trade evolution
            success, msg = await evolve_pokemon(
                session, poke, user.telegram_id, use_item="linking cord"
            )
            if success:
                await session.refresh(poke)
                await message.answer(
                    f"<b>Linking Cord Used!</b>\n\n"
                    f"{msg}\n\n"
                    f"Your Pokemon is now a <b>{poke.species.name}</b>!"
                )
            else:
                await message.answer(
                    f"Cannot use Linking Cord on {poke.display_name}.\n{msg}"
                )
            return

        # Regular evolution item
        success, msg = await evolve_pokemon(
            session, poke, user.telegram_id, use_item=item.name
        )
        if success:
            await session.refresh(poke)
            await message.answer(
                f"<b>{item.name} Used!</b>\n\n"
                f"{msg}\n\n"
                f"Your Pokemon is now a <b>{poke.species.name}</b>!"
            )
        else:
            await message.answer(
                f"Cannot use {item.name} on {poke.display_name}.\n{msg}"
            )
        return

    # ── Rare Candy ──
    if item_id == RARE_CANDY_ID:
        poke = await _resolve_use_target(session, user, pokemon_idx)
        if poke is None:
            await message.answer(
                "Please specify which Pokemon to use the Rare Candy on!\n"
                "Usage: /use 201 [pokemon#]\n"
                "Example: /use 201 1"
            )
            return

        if poke.level >= 100:
            await message.answer(f"{poke.display_name} is already at max level!")
            return

        # Use the rare candy
        poke.level += 1
        poke.friendship = min(255, poke.friendship + 3)
        inventory_item.quantity -= 1
        await session.commit()

        await message.answer(
            f"<b>Rare Candy Used!</b>\n\n"
            f"{poke.display_name} grew to Lv.{poke.level}!\n\n"
            f"<i>Rare Candies remaining: {inventory_item.quantity}</i>"
        )

        logger.info(
            "User used rare candy",
            user_id=user.telegram_id,
            pokemon=poke.species.name,
            new_level=poke.level,
        )

        # Update quest progress for item usage
        from telemon.core.quests import update_quest_progress
        await update_quest_progress(session, user.telegram_id, "use_item")
        await session.commit()

        # Check if can evolve now
        evo_result = await check_evolution(session, poke, user.telegram_id)
        if evo_result.can_evolve and evo_result.trigger == "level":
            await message.answer(
                f"{poke.display_name} is ready to evolve! Use /evolve to evolve it."
            )
        return

    # ── Soothe Bell ──
    if item_id == SOOTHE_BELL_ID:
        poke = await _resolve_use_target(session, user, pokemon_idx)
        if poke is None:
            await message.answer(
                "Please specify which Pokemon to give the Soothe Bell to!\n"
                "Usage: /use 30 [pokemon#]"
            )
            return

        poke.held_item = "Soothe Bell"
        await session.commit()

        await message.answer(
            f"<b>Soothe Bell</b>\n\n"
            f"{poke.display_name} is now holding a Soothe Bell!\n"
            f"Friendship gains are doubled while holding this item.\n\n"
            f"Current friendship: {poke.friendship}/255"
        )
        return

    # ── Incense ──
    if item_id == 202:
        await message.answer(
            "<b>Incense</b>\n\n"
            "Incense feature coming soon!\n"
            "When activated, Pokemon will spawn in your DMs for 1 hour."
        )
        return

    # ── XP Boost ──
    if item_id == 203:
        await message.answer(
            "<b>XP Boost</b>\n\n"
            "XP Boost feature coming soon!\n"
            "When activated, you'll earn 2x XP for 1 hour."
        )
        return

    # ── Battle items ──
    if category == "battle":
        poke = await _resolve_use_target(session, user, pokemon_idx)
        if poke is None:
            await message.answer(
                f"Please specify which Pokemon to give {item.name} to!\n"
                f"Usage: /use {item_id} [pokemon#]"
            )
            return

        poke.held_item = item.name
        await session.commit()

        await message.answer(
            f"<b>{item.name} Equipped!</b>\n\n"
            f"{poke.display_name} is now holding {item.name}."
        )
        return

    # ── Mega stones ──
    if category == "mega_stone":
        poke = await _resolve_use_target(session, user, pokemon_idx)
        if poke is None:
            await message.answer(
                f"Please specify which Pokemon to give {item.name} to!\n"
                f"Usage: /use {item_id} [pokemon#]"
            )
            return

        # Check if the Pokemon can actually mega evolve with this stone
        from telemon.core.forms import can_mega_evolve
        mega = can_mega_evolve(poke.species_id, item.name_lower)
        warning = ""
        if not mega:
            warning = (
                f"\n\n<i>Note: {poke.display_name} cannot mega evolve "
                f"with this stone. It may work on a different Pokemon.</i>"
            )

        poke.held_item = item.name
        await session.commit()

        await message.answer(
            f"<b>{item.name} Equipped!</b>\n\n"
            f"{poke.display_name} is now holding {item.name}.{warning}"
        )
        return

    await message.answer(
        f"Cannot use {item.name} directly.\n"
        f"Check /help for how to use this item."
    )


@router.message(Command("pet"))
async def cmd_pet(message: Message, session: AsyncSession, user: User) -> None:
    """Handle /pet command to increase friendship of selected Pokemon."""
    text = message.text or ""
    args = text.split()

    arg = args[1] if len(args) >= 2 else None
    poke = await _resolve_use_target(session, user, int(arg) if arg and arg.isdigit() else None)

    if not poke:
        await message.answer(
            "No Pokemon selected!\n"
            "Usage: /pet [pokemon#] or /pet (uses selected Pokemon)"
        )
        return

    if poke.friendship >= 255:
        await message.answer(
            f"{poke.display_name} already has maximum friendship! (255/255)\n"
            f"❤️ Your bond couldn't be stronger!"
        )
        return

    # Calculate friendship gain
    gain = PET_FRIENDSHIP_GAIN
    has_soothe_bell = poke.held_item and poke.held_item.lower() == "soothe bell"
    if has_soothe_bell:
        gain *= SOOTHE_BELL_MULTIPLIER

    old_friendship = poke.friendship
    poke.friendship = min(255, poke.friendship + gain)
    actual_gain = poke.friendship - old_friendship
    await session.commit()

    bell_text = " (Soothe Bell bonus!)" if has_soothe_bell else ""
    hearts = "❤️" * min(5, poke.friendship // 50)

    response = (
        f"You pet <b>{poke.display_name}</b>!\n"
        f"Friendship: {poke.friendship}/255 (+{actual_gain}{bell_text})\n"
        f"{hearts}"
    )

    # Update quest progress
    from telemon.core.quests import update_quest_progress

    completed = await update_quest_progress(session, user.telegram_id, "pet")
    if completed:
        await session.commit()
        for q in completed:
            response += f"\n📋 Quest complete: {q.description} (+{q.reward_coins:,} TC)"

    # Check if can evolve with friendship now
    evo_result = await check_evolution(session, poke, user.telegram_id)
    if evo_result.can_evolve and evo_result.trigger == "friendship":
        response += f"\n\n{poke.display_name} is ready to evolve! Use /evolve to evolve it."

    await message.answer(response)


async def _resolve_use_target(
    session: AsyncSession, user: User, pokemon_idx: int | None
) -> Pokemon | None:
    """Resolve a Pokemon target by index or selected Pokemon."""
    if pokemon_idx is not None:
        # Get by index
        poke_result = await session.execute(
            select(Pokemon)
            .where(Pokemon.owner_id == user.telegram_id)
            .order_by(Pokemon.caught_at.asc())
        )
        pokemon_list = list(poke_result.scalars().all())

        if pokemon_idx < 1 or pokemon_idx > len(pokemon_list):
            return None
        return pokemon_list[pokemon_idx - 1]

    # Use selected Pokemon
    if user.selected_pokemon_id:
        sel_result = await session.execute(
            select(Pokemon)
            .where(Pokemon.id == user.selected_pokemon_id)
            .where(Pokemon.owner_id == user.telegram_id)
        )
        return sel_result.scalar_one_or_none()

    return None
