"""Battle-related handlers for PvP duels."""

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from telemon.core.battle import (
    get_active_battle,
    create_battle,
    start_battle,
    execute_move,
    forfeit_battle,
    cancel_battle,
    MoveData,
)
from telemon.database.models import Pokemon, User
from telemon.database.models.battle import Battle, BattleStatus
from telemon.logging import get_logger

router = Router(name="battle")
logger = get_logger(__name__)


def format_hp_bar(current: int, maximum: int, length: int = 10) -> str:
    """Create a visual HP bar."""
    filled = int((current / maximum) * length) if maximum > 0 else 0
    empty = length - filled
    
    if current / maximum > 0.5:
        bar_char = ""
    elif current / maximum > 0.2:
        bar_char = ""
    else:
        bar_char = ""
    
    return f"[{'█' * filled}{'░' * empty}] {current}/{maximum}"


async def format_battle_status(session: AsyncSession, battle: Battle) -> str:
    """Format the current battle status."""
    # Get players
    p1_result = await session.execute(
        select(User).where(User.telegram_id == battle.player1_id)
    )
    p1 = p1_result.scalar_one()
    
    p2_result = await session.execute(
        select(User).where(User.telegram_id == battle.player2_id)
    )
    p2 = p2_result.scalar_one()
    
    # Get Pokemon
    p1_poke_result = await session.execute(
        select(Pokemon).where(Pokemon.id == battle.player1_team[0])
    )
    p1_poke = p1_poke_result.scalar_one()
    
    p2_poke_result = await session.execute(
        select(Pokemon).where(Pokemon.id == battle.player2_team[0])
    )
    p2_poke = p2_poke_result.scalar_one()
    
    p1_hp = battle.battle_state.get("p1_hp", 0)
    p1_max = battle.battle_state.get("p1_max_hp", 1)
    p2_hp = battle.battle_state.get("p2_hp", 0)
    p2_max = battle.battle_state.get("p2_max_hp", 1)
    
    p1_name = p1.username or f"Player {battle.player1_id}"
    p2_name = p2.username or f"Player {battle.player2_id}"
    
    whose_turn_name = p1_name if battle.whose_turn == battle.player1_id else p2_name
    
    lines = [
        f"<b>Battle - Turn {battle.current_turn}</b>\n",
        f"<b>{p1_name}</b>",
        f"{p1_poke.species.name} Lv.{p1_poke.level}",
        f"HP: {format_hp_bar(p1_hp, p1_max)}",
        "",
        f"<b>{p2_name}</b>",
        f"{p2_poke.species.name} Lv.{p2_poke.level}",
        f"HP: {format_hp_bar(p2_hp, p2_max)}",
        "",
        f"<b>{whose_turn_name}'s turn!</b>",
    ]
    
    return "\n".join(lines)


def build_move_keyboard(battle: Battle, user_id: int) -> InlineKeyboardBuilder:
    """Build move selection keyboard."""
    builder = InlineKeyboardBuilder()
    
    is_p1 = user_id == battle.player1_id
    moves = battle.battle_state.get("p1_moves" if is_p1 else "p2_moves", [])
    
    for i, move in enumerate(moves):
        # Show move name and type
        move_text = f"{move['name']} ({move['type'].title()})"
        builder.button(text=move_text, callback_data=f"battle:move:{battle.id}:{i}")
    
    builder.button(text="Forfeit", callback_data=f"battle:forfeit:{battle.id}")
    builder.adjust(2)
    
    return builder


@router.message(Command("duel", "battle"))
async def cmd_duel(message: Message, session: AsyncSession, user: User) -> None:
    """Handle /duel command to challenge another user."""
    text = message.text or ""
    args = text.split()
    
    if len(args) < 2:
        await message.answer(
            "<b>Battle System</b>\n\n"
            "Challenge another trainer to a 1v1 battle!\n\n"
            "<b>Usage:</b>\n"
            "/duel @username - Challenge by username\n"
            "/duel [user_id] - Challenge by ID\n\n"
            "<b>During Battle:</b>\n"
            "Select moves using inline buttons\n"
            "Type effectiveness and stats matter!\n\n"
            "<i>Rewards: XP and Telecoins for winning</i>"
        )
        return
    
    # Check if user has an active battle
    active = await get_active_battle(session, user.telegram_id)
    if active:
        if active.status == BattleStatus.ACTIVE:
            await message.answer(
                " You're already in a battle!\n"
                "Use the move buttons or /forfeit to end it."
            )
        else:
            await message.answer(
                " You have a pending challenge!\n"
                "Wait for response or /forfeit to cancel."
            )
        return
    
    # Check if user has a selected Pokemon
    if not user.selected_pokemon_id:
        # Get their first Pokemon
        result = await session.execute(
            select(Pokemon)
            .where(Pokemon.owner_id == user.telegram_id)
            .order_by(Pokemon.caught_at.desc())
            .limit(1)
        )
        first_poke = result.scalar_one_or_none()
        
        if not first_poke:
            await message.answer(
                " You don't have any Pokemon!\n"
                "Catch some first before battling."
            )
            return
        
        user.selected_pokemon_id = str(first_poke.id)
        await session.commit()
    
    # Parse target
    target_arg = args[1]
    target_user = None
    
    if target_arg.startswith("@"):
        # By username
        username = target_arg[1:]
        result = await session.execute(
            select(User).where(User.username.ilike(username))
        )
        target_user = result.scalar_one_or_none()
        
        if not target_user:
            await message.answer(f" User @{username} not found.")
            return
    elif target_arg.isdigit():
        # By ID
        result = await session.execute(
            select(User).where(User.telegram_id == int(target_arg))
        )
        target_user = result.scalar_one_or_none()
        
        if not target_user:
            await message.answer(f" User {target_arg} not found.")
            return
    else:
        await message.answer(" Please provide a valid @username or user ID.")
        return
    
    # Can't battle yourself
    if target_user.telegram_id == user.telegram_id:
        await message.answer(" You can't battle yourself!")
        return
    
    # Check if target is in a battle
    target_battle = await get_active_battle(session, target_user.telegram_id)
    if target_battle:
        await message.answer(
            f" @{target_user.username or target_user.telegram_id} is already in a battle!"
        )
        return
    
    # Get challenger's Pokemon
    challenger_poke_result = await session.execute(
        select(Pokemon).where(Pokemon.id == user.selected_pokemon_id)
    )
    challenger_poke = challenger_poke_result.scalar_one_or_none()
    
    if not challenger_poke:
        await message.answer(" Your selected Pokemon was not found!")
        return
    
    # Create battle challenge
    battle = await create_battle(
        session,
        challenger_id=user.telegram_id,
        opponent_id=target_user.telegram_id,
        challenger_pokemon_id=user.selected_pokemon_id,
        chat_id=message.chat.id,
    )
    
    logger.info(
        "Battle challenge created",
        challenger_id=user.telegram_id,
        opponent_id=target_user.telegram_id,
        battle_id=str(battle.id),
    )
    
    # Build accept/decline keyboard
    builder = InlineKeyboardBuilder()
    builder.button(text="Accept", callback_data=f"battle:accept:{battle.id}")
    builder.button(text="Decline", callback_data=f"battle:decline:{battle.id}")
    builder.adjust(2)
    
    target_name = target_user.username or f"User {target_user.telegram_id}"
    challenger_name = user.username or f"User {user.telegram_id}"
    
    await message.answer(
        f"<b>Battle Challenge!</b>\n\n"
        f"@{challenger_name} challenges @{target_name}!\n\n"
        f"<b>{challenger_name}'s Pokemon:</b>\n"
        f"{challenger_poke.species.name} Lv.{challenger_poke.level}\n\n"
        f"@{target_name}, select your Pokemon and accept!",
        reply_markup=builder.as_markup(),
    )


@router.callback_query(lambda c: c.data and c.data.startswith("battle:accept:"))
async def callback_accept_battle(
    callback: CallbackQuery, session: AsyncSession, user: User
) -> None:
    """Handle battle acceptance."""
    if not callback.data:
        return
    
    battle_id = callback.data.split(":")[2]
    
    result = await session.execute(
        select(Battle).where(Battle.id == battle_id)
    )
    battle = result.scalar_one_or_none()
    
    if not battle:
        await callback.answer("Battle not found!", show_alert=True)
        return
    
    if battle.player2_id != user.telegram_id:
        await callback.answer("This challenge is not for you!", show_alert=True)
        return
    
    if battle.status != BattleStatus.PENDING:
        await callback.answer("This battle is no longer available!", show_alert=True)
        return
    
    # Check if defender has a Pokemon
    if not user.selected_pokemon_id:
        # Get their first Pokemon
        poke_result = await session.execute(
            select(Pokemon)
            .where(Pokemon.owner_id == user.telegram_id)
            .order_by(Pokemon.caught_at.desc())
            .limit(1)
        )
        first_poke = poke_result.scalar_one_or_none()
        
        if not first_poke:
            await callback.answer("You don't have any Pokemon!", show_alert=True)
            return
        
        user.selected_pokemon_id = str(first_poke.id)
        await session.commit()
    
    # Start the battle
    battle_info = await start_battle(session, battle, user.selected_pokemon_id)
    
    logger.info(
        "Battle started",
        battle_id=str(battle.id),
        p1_pokemon=battle_info["p1_pokemon"].species.name,
        p2_pokemon=battle_info["p2_pokemon"].species.name,
    )
    
    # Get the player whose turn it is
    first_player_id = battle_info["first_turn"]
    
    # Format battle status
    status = await format_battle_status(session, battle)
    
    # Build move keyboard for first player
    builder = build_move_keyboard(battle, first_player_id)
    
    await callback.message.edit_text(
        f"<b>Battle Started!</b>\n\n"
        f"{battle_info['p1_pokemon'].species.name} vs {battle_info['p2_pokemon'].species.name}\n\n"
        f"{status}",
        reply_markup=builder.as_markup(),
    )
    await callback.answer("Battle started!")


@router.callback_query(lambda c: c.data and c.data.startswith("battle:decline:"))
async def callback_decline_battle(
    callback: CallbackQuery, session: AsyncSession, user: User
) -> None:
    """Handle battle decline."""
    if not callback.data:
        return
    
    battle_id = callback.data.split(":")[2]
    
    result = await session.execute(
        select(Battle).where(Battle.id == battle_id)
    )
    battle = result.scalar_one_or_none()
    
    if not battle:
        await callback.answer("Battle not found!", show_alert=True)
        return
    
    if battle.player2_id != user.telegram_id:
        await callback.answer("This challenge is not for you!", show_alert=True)
        return
    
    if battle.status != BattleStatus.PENDING:
        await callback.answer("This battle is no longer available!", show_alert=True)
        return
    
    await cancel_battle(session, battle)
    
    await callback.message.edit_text(" Battle declined.")
    await callback.answer("Battle declined!")


@router.callback_query(lambda c: c.data and c.data.startswith("battle:move:"))
async def callback_execute_move(
    callback: CallbackQuery, session: AsyncSession, user: User
) -> None:
    """Handle move selection."""
    if not callback.data:
        return
    
    parts = callback.data.split(":")
    battle_id = parts[2]
    move_index = int(parts[3])
    
    result = await session.execute(
        select(Battle).where(Battle.id == battle_id)
    )
    battle = result.scalar_one_or_none()
    
    if not battle:
        await callback.answer("Battle not found!", show_alert=True)
        return
    
    if battle.status != BattleStatus.ACTIVE:
        await callback.answer("This battle has ended!", show_alert=True)
        return
    
    # Check if it's the user's turn
    if battle.whose_turn != user.telegram_id:
        await callback.answer("It's not your turn!", show_alert=True)
        return
    
    # Execute the move
    move_result = await execute_move(session, battle, user.telegram_id, move_index)
    
    # Build message
    lines = [move_result["message"]]
    
    if move_result["damage"] > 0:
        lines.append(f"Dealt <b>{move_result['damage']}</b> damage!")
    
    if move_result["battle_ended"]:
        # Battle is over
        winner_result = await session.execute(
            select(User).where(User.telegram_id == move_result["winner_id"])
        )
        winner = winner_result.scalar_one()
        
        # Award rewards
        winner.balance += move_result["winner_coins"]
        
        # Add XP to winner's Pokemon
        winner_poke_id = (battle.player1_team[0] if move_result["winner_id"] == battle.player1_id 
                         else battle.player2_team[0])
        winner_poke_result = await session.execute(
            select(Pokemon).where(Pokemon.id == winner_poke_id)
        )
        winner_poke = winner_poke_result.scalar_one()
        winner_poke.experience += move_result["winner_xp"]
        
        # Check for level up (simple formula)
        xp_needed = winner_poke.level * 100
        while winner_poke.experience >= xp_needed and winner_poke.level < 100:
            winner_poke.level += 1
            winner_poke.experience -= xp_needed
            xp_needed = winner_poke.level * 100
        
        await session.commit()
        
        winner_name = winner.username or f"User {winner.telegram_id}"
        
        lines.extend([
            "",
            f"<b>{move_result['defender'].species.name} fainted!</b>",
            "",
            f"<b>@{winner_name} wins!</b>",
            f"Rewards: {move_result['winner_xp']} XP, {move_result['winner_coins']} TC",
        ])
        
        logger.info(
            "Battle completed",
            battle_id=str(battle.id),
            winner_id=move_result["winner_id"],
            turns=battle.current_turn,
        )
        
        await callback.message.edit_text("\n".join(lines))
    else:
        # Battle continues - refresh and show next player's turn
        await session.refresh(battle)
        
        status = await format_battle_status(session, battle)
        
        builder = build_move_keyboard(battle, battle.whose_turn)
        
        lines.extend(["", status])
        
        await callback.message.edit_text(
            "\n".join(lines),
            reply_markup=builder.as_markup(),
        )
    
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("battle:forfeit:"))
async def callback_forfeit_battle(
    callback: CallbackQuery, session: AsyncSession, user: User
) -> None:
    """Handle battle forfeit."""
    if not callback.data:
        return
    
    battle_id = callback.data.split(":")[2]
    
    result = await session.execute(
        select(Battle).where(Battle.id == battle_id)
    )
    battle = result.scalar_one_or_none()
    
    if not battle:
        await callback.answer("Battle not found!", show_alert=True)
        return
    
    if user.telegram_id not in [battle.player1_id, battle.player2_id]:
        await callback.answer("You're not in this battle!", show_alert=True)
        return
    
    if battle.status not in [BattleStatus.PENDING, BattleStatus.ACTIVE]:
        await callback.answer("This battle has already ended!", show_alert=True)
        return
    
    winner_id = await forfeit_battle(session, battle, user.telegram_id)
    
    winner_result = await session.execute(
        select(User).where(User.telegram_id == winner_id)
    )
    winner = winner_result.scalar_one()
    winner_name = winner.username or f"User {winner_id}"
    
    forfeiter_name = user.username or f"User {user.telegram_id}"
    
    logger.info(
        "Battle forfeited",
        battle_id=str(battle.id),
        forfeiter_id=user.telegram_id,
        winner_id=winner_id,
    )
    
    await callback.message.edit_text(
        f" @{forfeiter_name} forfeited!\n\n"
        f"@{winner_name} wins by forfeit!"
    )
    await callback.answer("Battle forfeited!")


@router.message(Command("forfeit"))
async def cmd_forfeit(message: Message, session: AsyncSession, user: User) -> None:
    """Handle /forfeit command."""
    battle = await get_active_battle(session, user.telegram_id)
    
    if not battle:
        await message.answer(" You don't have an active battle!")
        return
    
    winner_id = await forfeit_battle(session, battle, user.telegram_id)
    
    winner_result = await session.execute(
        select(User).where(User.telegram_id == winner_id)
    )
    winner = winner_result.scalar_one()
    winner_name = winner.username or f"User {winner_id}"
    
    await message.answer(
        f" You forfeited the battle!\n"
        f"@{winner_name} wins!"
    )
