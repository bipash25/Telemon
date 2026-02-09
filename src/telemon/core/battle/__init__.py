"""Battle system core logic."""

import random
from dataclasses import dataclass
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from telemon.database.models import Pokemon, PokemonSpecies, User
from telemon.database.models.battle import Battle, BattleStatus
from telemon.logging import get_logger

logger = get_logger(__name__)

# Type effectiveness chart (Gen 1)
# Format: ATTACKING_TYPE -> {DEFENDING_TYPE: multiplier}
TYPE_CHART = {
    "normal": {"rock": 0.5, "ghost": 0, "steel": 0.5},
    "fire": {"fire": 0.5, "water": 0.5, "grass": 2, "ice": 2, "bug": 2, "rock": 0.5, "dragon": 0.5, "steel": 2},
    "water": {"fire": 2, "water": 0.5, "grass": 0.5, "ground": 2, "rock": 2, "dragon": 0.5},
    "electric": {"water": 2, "electric": 0.5, "grass": 0.5, "ground": 0, "flying": 2, "dragon": 0.5},
    "grass": {"fire": 0.5, "water": 2, "grass": 0.5, "poison": 0.5, "ground": 2, "flying": 0.5, "bug": 0.5, "rock": 2, "dragon": 0.5, "steel": 0.5},
    "ice": {"fire": 0.5, "water": 0.5, "grass": 2, "ice": 0.5, "ground": 2, "flying": 2, "dragon": 2, "steel": 0.5},
    "fighting": {"normal": 2, "ice": 2, "poison": 0.5, "flying": 0.5, "psychic": 0.5, "bug": 0.5, "rock": 2, "ghost": 0, "dark": 2, "steel": 2, "fairy": 0.5},
    "poison": {"grass": 2, "poison": 0.5, "ground": 0.5, "rock": 0.5, "ghost": 0.5, "steel": 0, "fairy": 2},
    "ground": {"fire": 2, "electric": 2, "grass": 0.5, "poison": 2, "flying": 0, "bug": 0.5, "rock": 2, "steel": 2},
    "flying": {"electric": 0.5, "grass": 2, "fighting": 2, "bug": 2, "rock": 0.5, "steel": 0.5},
    "psychic": {"fighting": 2, "poison": 2, "psychic": 0.5, "dark": 0, "steel": 0.5},
    "bug": {"fire": 0.5, "grass": 2, "fighting": 0.5, "poison": 0.5, "flying": 0.5, "psychic": 2, "ghost": 0.5, "dark": 2, "steel": 0.5, "fairy": 0.5},
    "rock": {"fire": 2, "ice": 2, "fighting": 0.5, "ground": 0.5, "flying": 2, "bug": 2, "steel": 0.5},
    "ghost": {"normal": 0, "psychic": 2, "ghost": 2, "dark": 0.5},
    "dragon": {"dragon": 2, "steel": 0.5, "fairy": 0},
    "dark": {"fighting": 0.5, "psychic": 2, "ghost": 2, "dark": 0.5, "fairy": 0.5},
    "steel": {"fire": 0.5, "water": 0.5, "electric": 0.5, "ice": 2, "rock": 2, "steel": 0.5, "fairy": 2},
    "fairy": {"fire": 0.5, "fighting": 2, "poison": 0.5, "dragon": 2, "dark": 2, "steel": 0.5},
}

# Basic moves for each type (used when Pokemon has no moves)
DEFAULT_MOVES = {
    "normal": {"name": "Tackle", "power": 40, "accuracy": 100, "category": "physical"},
    "fire": {"name": "Ember", "power": 40, "accuracy": 100, "category": "special"},
    "water": {"name": "Water Gun", "power": 40, "accuracy": 100, "category": "special"},
    "electric": {"name": "Thunder Shock", "power": 40, "accuracy": 100, "category": "special"},
    "grass": {"name": "Vine Whip", "power": 45, "accuracy": 100, "category": "physical"},
    "ice": {"name": "Powder Snow", "power": 40, "accuracy": 100, "category": "special"},
    "fighting": {"name": "Karate Chop", "power": 50, "accuracy": 100, "category": "physical"},
    "poison": {"name": "Poison Sting", "power": 15, "accuracy": 100, "category": "physical"},
    "ground": {"name": "Mud-Slap", "power": 20, "accuracy": 100, "category": "special"},
    "flying": {"name": "Gust", "power": 40, "accuracy": 100, "category": "special"},
    "psychic": {"name": "Confusion", "power": 50, "accuracy": 100, "category": "special"},
    "bug": {"name": "Bug Bite", "power": 60, "accuracy": 100, "category": "physical"},
    "rock": {"name": "Rock Throw", "power": 50, "accuracy": 90, "category": "physical"},
    "ghost": {"name": "Lick", "power": 30, "accuracy": 100, "category": "physical"},
    "dragon": {"name": "Dragon Rage", "power": 40, "accuracy": 100, "category": "special"},
    "dark": {"name": "Bite", "power": 60, "accuracy": 100, "category": "physical"},
    "steel": {"name": "Metal Claw", "power": 50, "accuracy": 95, "category": "physical"},
    "fairy": {"name": "Fairy Wind", "power": 40, "accuracy": 100, "category": "special"},
}

# Additional powerful moves for diversity
STRONG_MOVES = {
    "fire": {"name": "Flamethrower", "power": 90, "accuracy": 100, "category": "special"},
    "water": {"name": "Surf", "power": 90, "accuracy": 100, "category": "special"},
    "electric": {"name": "Thunderbolt", "power": 90, "accuracy": 100, "category": "special"},
    "grass": {"name": "Solar Beam", "power": 120, "accuracy": 100, "category": "special"},
    "ice": {"name": "Ice Beam", "power": 90, "accuracy": 100, "category": "special"},
    "psychic": {"name": "Psychic", "power": 90, "accuracy": 100, "category": "special"},
    "fighting": {"name": "Close Combat", "power": 120, "accuracy": 100, "category": "physical"},
    "ground": {"name": "Earthquake", "power": 100, "accuracy": 100, "category": "physical"},
    "flying": {"name": "Aerial Ace", "power": 60, "accuracy": 100, "category": "physical"},
    "rock": {"name": "Rock Slide", "power": 75, "accuracy": 90, "category": "physical"},
    "ghost": {"name": "Shadow Ball", "power": 80, "accuracy": 100, "category": "special"},
    "dragon": {"name": "Dragon Claw", "power": 80, "accuracy": 100, "category": "physical"},
    "normal": {"name": "Body Slam", "power": 85, "accuracy": 100, "category": "physical"},
    "poison": {"name": "Sludge Bomb", "power": 90, "accuracy": 100, "category": "special"},
    "bug": {"name": "X-Scissor", "power": 80, "accuracy": 100, "category": "physical"},
    "dark": {"name": "Crunch", "power": 80, "accuracy": 100, "category": "physical"},
    "steel": {"name": "Iron Head", "power": 80, "accuracy": 100, "category": "physical"},
    "fairy": {"name": "Moonblast", "power": 95, "accuracy": 100, "category": "special"},
}


@dataclass
class MoveData:
    """Represents a move with its properties."""
    name: str
    type: str
    power: int
    accuracy: int
    category: str  # physical, special, status


@dataclass
class BattlePokemon:
    """Pokemon state during battle."""
    pokemon: Pokemon
    species: PokemonSpecies
    current_hp: int
    max_hp: int
    moves: list[MoveData]
    
    @property
    def is_fainted(self) -> bool:
        return self.current_hp <= 0


@dataclass
class DamageResult:
    """Result of a damage calculation."""
    damage: int
    effectiveness: float
    is_critical: bool
    message: str


def get_type_effectiveness(attacking_type: str, defending_types: list[str]) -> float:
    """Calculate type effectiveness multiplier."""
    multiplier = 1.0
    
    for def_type in defending_types:
        if attacking_type in TYPE_CHART:
            multiplier *= TYPE_CHART[attacking_type].get(def_type, 1.0)
    
    return multiplier


def get_effectiveness_message(multiplier: float) -> str:
    """Get effectiveness message based on multiplier."""
    if multiplier == 0:
        return "It had no effect..."
    elif multiplier < 1:
        return "It's not very effective..."
    elif multiplier > 1:
        return "It's super effective!"
    return ""


def calculate_stat(base: int, iv: int, ev: int, level: int, is_hp: bool = False) -> int:
    """Calculate actual stat value using Pokemon formula."""
    if is_hp:
        return ((2 * base + iv + ev // 4) * level) // 100 + level + 10
    else:
        return ((2 * base + iv + ev // 4) * level) // 100 + 5


def get_pokemon_moves(pokemon: Pokemon, species: PokemonSpecies) -> list[MoveData]:
    """Get moves for a Pokemon. Uses default moves if none are set."""
    moves = []
    
    # Add primary type move
    type1 = species.type1.lower()
    if type1 in DEFAULT_MOVES:
        move = DEFAULT_MOVES[type1]
        moves.append(MoveData(
            name=move["name"],
            type=type1,
            power=move["power"],
            accuracy=move["accuracy"],
            category=move["category"],
        ))
    
    # Add secondary type move if exists
    if species.type2:
        type2 = species.type2.lower()
        if type2 in DEFAULT_MOVES:
            move = DEFAULT_MOVES[type2]
            moves.append(MoveData(
                name=move["name"],
                type=type2,
                power=move["power"],
                accuracy=move["accuracy"],
                category=move["category"],
            ))
    
    # Add a normal move for coverage
    if type1 != "normal":
        move = DEFAULT_MOVES["normal"]
        moves.append(MoveData(
            name=move["name"],
            type="normal",
            power=move["power"],
            accuracy=move["accuracy"],
            category=move["category"],
        ))
    
    # Add a strong move if level is high enough
    if pokemon.level >= 30:
        if type1 in STRONG_MOVES:
            move = STRONG_MOVES[type1]
            moves.append(MoveData(
                name=move["name"],
                type=type1,
                power=move["power"],
                accuracy=move["accuracy"],
                category=move["category"],
            ))
    
    return moves[:4]  # Max 4 moves


def create_battle_pokemon(pokemon: Pokemon, species: PokemonSpecies) -> BattlePokemon:
    """Create a BattlePokemon from a Pokemon instance."""
    max_hp = calculate_stat(
        species.base_hp, pokemon.iv_hp, pokemon.ev_hp, pokemon.level, is_hp=True
    )
    
    return BattlePokemon(
        pokemon=pokemon,
        species=species,
        current_hp=max_hp,
        max_hp=max_hp,
        moves=get_pokemon_moves(pokemon, species),
    )


def calculate_damage(
    attacker: BattlePokemon,
    defender: BattlePokemon,
    move: MoveData,
) -> DamageResult:
    """Calculate damage for an attack."""
    # Check accuracy
    if random.randint(1, 100) > move.accuracy:
        return DamageResult(
            damage=0,
            effectiveness=1.0,
            is_critical=False,
            message=f"{attacker.species.name}'s attack missed!",
        )
    
    # Get attacker stats
    level = attacker.pokemon.level
    
    if move.category == "physical":
        attack_stat = calculate_stat(
            attacker.species.base_attack,
            attacker.pokemon.iv_attack,
            attacker.pokemon.ev_attack,
            level,
        )
        defense_stat = calculate_stat(
            defender.species.base_defense,
            defender.pokemon.iv_defense,
            defender.pokemon.ev_defense,
            defender.pokemon.level,
        )
    else:  # special
        attack_stat = calculate_stat(
            attacker.species.base_sp_attack,
            attacker.pokemon.iv_sp_attack,
            attacker.pokemon.ev_sp_attack,
            level,
        )
        defense_stat = calculate_stat(
            defender.species.base_sp_defense,
            defender.pokemon.iv_sp_defense,
            defender.pokemon.ev_sp_defense,
            defender.pokemon.level,
        )
    
    # Base damage calculation
    base_damage = (((2 * level / 5 + 2) * move.power * attack_stat / defense_stat) / 50 + 2)
    
    # STAB (Same Type Attack Bonus)
    stab = 1.5 if move.type in [attacker.species.type1.lower(), 
                                 (attacker.species.type2 or "").lower()] else 1.0
    
    # Type effectiveness
    defender_types = [defender.species.type1.lower()]
    if defender.species.type2:
        defender_types.append(defender.species.type2.lower())
    effectiveness = get_type_effectiveness(move.type, defender_types)
    
    # Critical hit (6.25% chance)
    is_critical = random.random() < 0.0625
    crit_multiplier = 1.5 if is_critical else 1.0
    
    # Random factor (85-100%)
    random_factor = random.randint(85, 100) / 100
    
    # Final damage
    damage = int(base_damage * stab * effectiveness * crit_multiplier * random_factor)
    damage = max(1, damage)  # Minimum 1 damage
    
    if effectiveness == 0:
        damage = 0
    
    # Build message
    messages = [f"{attacker.species.name} used {move.name}!"]
    
    eff_msg = get_effectiveness_message(effectiveness)
    if eff_msg:
        messages.append(eff_msg)
    
    if is_critical:
        messages.append("A critical hit!")
    
    return DamageResult(
        damage=damage,
        effectiveness=effectiveness,
        is_critical=is_critical,
        message="\n".join(messages),
    )


async def get_active_battle(session: AsyncSession, user_id: int) -> Battle | None:
    """Get active battle for a user."""
    result = await session.execute(
        select(Battle)
        .where(
            ((Battle.player1_id == user_id) | (Battle.player2_id == user_id))
            & (Battle.status.in_([BattleStatus.PENDING, BattleStatus.ACTIVE]))
        )
    )
    return result.scalar_one_or_none()


async def create_battle(
    session: AsyncSession,
    challenger_id: int,
    opponent_id: int,
    challenger_pokemon_id: str,
    chat_id: int,
) -> Battle:
    """Create a new battle challenge."""
    import uuid
    
    battle = Battle(
        player1_id=challenger_id,
        player2_id=opponent_id,
        player1_team=[uuid.UUID(challenger_pokemon_id)],
        player2_team=[],
        status=BattleStatus.PENDING,
        chat_id=chat_id,
        battle_state={
            "p1_hp": None,  # Will be set when battle starts
            "p2_hp": None,
        },
    )
    session.add(battle)
    await session.commit()
    return battle


async def start_battle(session: AsyncSession, battle: Battle, defender_pokemon_id: str) -> dict:
    """Start a battle after acceptance."""
    import uuid
    from datetime import datetime
    
    battle.player2_team = [uuid.UUID(defender_pokemon_id)]
    battle.status = BattleStatus.ACTIVE
    battle.started_at = datetime.utcnow()
    
    # Load Pokemon
    p1_pokemon = await session.execute(
        select(Pokemon).where(Pokemon.id == battle.player1_team[0])
    )
    p1_poke = p1_pokemon.scalar_one()
    
    p2_pokemon = await session.execute(
        select(Pokemon).where(Pokemon.id == battle.player2_team[0])
    )
    p2_poke = p2_pokemon.scalar_one()
    
    # Create battle Pokemon
    bp1 = create_battle_pokemon(p1_poke, p1_poke.species)
    bp2 = create_battle_pokemon(p2_poke, p2_poke.species)
    
    # Determine who goes first based on speed
    p1_speed = calculate_stat(
        p1_poke.species.base_speed, p1_poke.iv_speed, p1_poke.ev_speed, p1_poke.level
    )
    p2_speed = calculate_stat(
        p2_poke.species.base_speed, p2_poke.iv_speed, p2_poke.ev_speed, p2_poke.level
    )
    
    if p1_speed > p2_speed:
        battle.whose_turn = battle.player1_id
    elif p2_speed > p1_speed:
        battle.whose_turn = battle.player2_id
    else:
        # Random if same speed
        battle.whose_turn = random.choice([battle.player1_id, battle.player2_id])
    
    # Store HP in battle state
    battle.battle_state = {
        "p1_hp": bp1.current_hp,
        "p1_max_hp": bp1.max_hp,
        "p2_hp": bp2.current_hp,
        "p2_max_hp": bp2.max_hp,
        "p1_moves": [{"name": m.name, "type": m.type, "power": m.power, "accuracy": m.accuracy, "category": m.category} for m in bp1.moves],
        "p2_moves": [{"name": m.name, "type": m.type, "power": m.power, "accuracy": m.accuracy, "category": m.category} for m in bp2.moves],
    }
    battle.battle_log = []
    
    await session.commit()
    
    return {
        "p1_pokemon": p1_poke,
        "p2_pokemon": p2_poke,
        "p1_bp": bp1,
        "p2_bp": bp2,
        "first_turn": battle.whose_turn,
    }


async def execute_move(
    session: AsyncSession,
    battle: Battle,
    attacker_id: int,
    move_index: int,
) -> dict:
    """Execute a move in battle."""
    from datetime import datetime
    
    is_p1 = attacker_id == battle.player1_id
    
    # Load Pokemon
    attacker_poke_id = battle.player1_team[0] if is_p1 else battle.player2_team[0]
    defender_poke_id = battle.player2_team[0] if is_p1 else battle.player1_team[0]
    
    attacker_result = await session.execute(
        select(Pokemon).where(Pokemon.id == attacker_poke_id)
    )
    attacker_poke = attacker_result.scalar_one()
    
    defender_result = await session.execute(
        select(Pokemon).where(Pokemon.id == defender_poke_id)
    )
    defender_poke = defender_result.scalar_one()
    
    # Get current HP from battle state
    attacker_hp = battle.battle_state["p1_hp"] if is_p1 else battle.battle_state["p2_hp"]
    attacker_max_hp = battle.battle_state["p1_max_hp"] if is_p1 else battle.battle_state["p2_max_hp"]
    defender_hp = battle.battle_state["p2_hp"] if is_p1 else battle.battle_state["p1_hp"]
    defender_max_hp = battle.battle_state["p2_max_hp"] if is_p1 else battle.battle_state["p1_max_hp"]
    
    # Get moves
    moves_data = battle.battle_state["p1_moves"] if is_p1 else battle.battle_state["p2_moves"]
    if move_index >= len(moves_data):
        move_index = 0
    
    move_data = moves_data[move_index]
    move = MoveData(
        name=move_data["name"],
        type=move_data["type"],
        power=move_data["power"],
        accuracy=move_data["accuracy"],
        category=move_data["category"],
    )
    
    # Create battle Pokemon objects
    attacker_bp = BattlePokemon(
        pokemon=attacker_poke,
        species=attacker_poke.species,
        current_hp=attacker_hp,
        max_hp=attacker_max_hp,
        moves=[move],
    )
    
    defender_bp = BattlePokemon(
        pokemon=defender_poke,
        species=defender_poke.species,
        current_hp=defender_hp,
        max_hp=defender_max_hp,
        moves=[],
    )
    
    # Calculate and apply damage
    result = calculate_damage(attacker_bp, defender_bp, move)
    new_defender_hp = max(0, defender_hp - result.damage)
    
    # Update battle state
    if is_p1:
        battle.battle_state["p2_hp"] = new_defender_hp
    else:
        battle.battle_state["p1_hp"] = new_defender_hp
    
    # Add to battle log
    log_entry = {
        "turn": battle.current_turn,
        "attacker": attacker_id,
        "move": move.name,
        "damage": result.damage,
        "effectiveness": result.effectiveness,
        "critical": result.is_critical,
    }
    battle.battle_log = battle.battle_log + [log_entry]
    
    battle.last_action_at = datetime.utcnow()
    
    # Check for battle end
    battle_ended = False
    winner_id = None
    
    if new_defender_hp <= 0:
        battle_ended = True
        winner_id = attacker_id
        battle.status = BattleStatus.COMPLETED
        battle.winner_id = winner_id
        battle.ended_at = datetime.utcnow()
        
        # Calculate rewards
        level_diff = attacker_poke.level - defender_poke.level
        base_xp = 50 + defender_poke.level * 5
        base_coins = 100 + defender_poke.level * 10
        
        # Bonus for beating higher level
        if level_diff < 0:
            base_xp = int(base_xp * (1 + abs(level_diff) * 0.1))
            base_coins = int(base_coins * (1 + abs(level_diff) * 0.1))
        
        battle.winner_xp = base_xp
        battle.winner_coins = base_coins
    else:
        # Switch turns
        battle.whose_turn = battle.player2_id if is_p1 else battle.player1_id
        battle.current_turn += 1
    
    await session.commit()
    
    return {
        "message": result.message,
        "damage": result.damage,
        "effectiveness": result.effectiveness,
        "is_critical": result.is_critical,
        "attacker": attacker_poke,
        "defender": defender_poke,
        "defender_hp": new_defender_hp,
        "defender_max_hp": defender_max_hp,
        "battle_ended": battle_ended,
        "winner_id": winner_id,
        "winner_xp": battle.winner_xp if battle_ended else 0,
        "winner_coins": battle.winner_coins if battle_ended else 0,
    }


async def forfeit_battle(session: AsyncSession, battle: Battle, forfeiter_id: int) -> int:
    """Forfeit a battle and return the winner's ID."""
    from datetime import datetime
    
    winner_id = battle.player2_id if forfeiter_id == battle.player1_id else battle.player1_id
    
    battle.status = BattleStatus.FORFEITED
    battle.winner_id = winner_id
    battle.ended_at = datetime.utcnow()
    
    await session.commit()
    
    return winner_id


async def cancel_battle(session: AsyncSession, battle: Battle) -> None:
    """Cancel a pending battle."""
    battle.status = BattleStatus.CANCELLED
    await session.commit()
