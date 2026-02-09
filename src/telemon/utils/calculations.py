"""Pokemon stat calculations."""

import json
from functools import lru_cache
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"


@lru_cache(maxsize=1)
def load_natures() -> dict:
    """Load natures data."""
    with open(DATA_DIR / "natures.json") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def load_type_chart() -> dict:
    """Load type effectiveness chart."""
    with open(DATA_DIR / "type_chart.json") as f:
        return json.load(f)


def get_nature_multiplier(nature: str, stat: str) -> float:
    """Get the nature multiplier for a stat.

    Args:
        nature: The nature name (lowercase)
        stat: The stat name (hp, attack, defense, sp_attack, sp_defense, speed)

    Returns:
        1.1 if boosted, 0.9 if reduced, 1.0 otherwise
    """
    natures = load_natures()
    nature_data = natures.get(nature.lower(), {})

    if nature_data.get("increased") == stat:
        return 1.1
    elif nature_data.get("decreased") == stat:
        return 0.9
    return 1.0


def calculate_stat(
    base_stat: int,
    iv: int,
    ev: int,
    level: int,
    nature_multiplier: float = 1.0,
    is_hp: bool = False,
) -> int:
    """Calculate a Pokemon's stat using the standard formula.

    Args:
        base_stat: The base stat value
        iv: Individual value (0-31)
        ev: Effort value (0-252)
        level: Pokemon's level (1-100)
        nature_multiplier: Nature modifier (0.9, 1.0, or 1.1)
        is_hp: Whether this is the HP stat

    Returns:
        The calculated stat value
    """
    # Standard Pokemon stat formula
    if is_hp:
        # HP formula: floor((2 * Base + IV + floor(EV/4)) * Level / 100) + Level + 10
        stat = int(((2 * base_stat + iv + int(ev / 4)) * level / 100) + level + 10)
    else:
        # Other stats: floor((floor((2 * Base + IV + floor(EV/4)) * Level / 100) + 5) * Nature)
        stat = int((int((2 * base_stat + iv + int(ev / 4)) * level / 100) + 5) * nature_multiplier)

    return stat


def calculate_all_stats(
    base_hp: int,
    base_attack: int,
    base_defense: int,
    base_sp_attack: int,
    base_sp_defense: int,
    base_speed: int,
    iv_hp: int,
    iv_attack: int,
    iv_defense: int,
    iv_sp_attack: int,
    iv_sp_defense: int,
    iv_speed: int,
    ev_hp: int,
    ev_attack: int,
    ev_defense: int,
    ev_sp_attack: int,
    ev_sp_defense: int,
    ev_speed: int,
    level: int,
    nature: str,
) -> dict[str, int]:
    """Calculate all stats for a Pokemon.

    Returns:
        Dictionary with all calculated stats
    """
    return {
        "hp": calculate_stat(base_hp, iv_hp, ev_hp, level, is_hp=True),
        "attack": calculate_stat(
            base_attack, iv_attack, ev_attack, level,
            get_nature_multiplier(nature, "attack")
        ),
        "defense": calculate_stat(
            base_defense, iv_defense, ev_defense, level,
            get_nature_multiplier(nature, "defense")
        ),
        "sp_attack": calculate_stat(
            base_sp_attack, iv_sp_attack, ev_sp_attack, level,
            get_nature_multiplier(nature, "sp_attack")
        ),
        "sp_defense": calculate_stat(
            base_sp_defense, iv_sp_defense, ev_sp_defense, level,
            get_nature_multiplier(nature, "sp_defense")
        ),
        "speed": calculate_stat(
            base_speed, iv_speed, ev_speed, level,
            get_nature_multiplier(nature, "speed")
        ),
    }


def calculate_experience_for_level(level: int, growth_rate: str = "medium") -> int:
    """Calculate total experience needed for a level.

    Args:
        level: Target level (1-100)
        growth_rate: Growth rate type

    Returns:
        Total experience points needed
    """
    n = level

    growth_formulas = {
        "slow": lambda n: (5 * n**3) // 4,
        "medium": lambda n: n**3,
        "medium-slow": lambda n: int((6/5 * n**3) - (15 * n**2) + (100 * n) - 140),
        "fast": lambda n: (4 * n**3) // 5,
        "erratic": lambda n: _erratic_exp(n),
        "fluctuating": lambda n: _fluctuating_exp(n),
    }

    formula = growth_formulas.get(growth_rate, growth_formulas["medium"])
    return max(0, formula(n))


def _erratic_exp(n: int) -> int:
    """Calculate erratic growth rate experience."""
    if n <= 50:
        return int((n**3 * (100 - n)) / 50)
    elif n <= 68:
        return int((n**3 * (150 - n)) / 100)
    elif n <= 98:
        return int((n**3 * ((1911 - 10 * n) / 3)) / 500)
    else:
        return int((n**3 * (160 - n)) / 100)


def _fluctuating_exp(n: int) -> int:
    """Calculate fluctuating growth rate experience."""
    if n <= 15:
        return int(n**3 * ((((n + 1) / 3) + 24) / 50))
    elif n <= 36:
        return int(n**3 * ((n + 14) / 50))
    else:
        return int(n**3 * (((n / 2) + 32) / 50))


def get_type_effectiveness(attack_type: str, defending_types: list[str]) -> float:
    """Get type effectiveness multiplier.

    Args:
        attack_type: The attacking move's type
        defending_types: List of defender's types

    Returns:
        Effectiveness multiplier (0, 0.25, 0.5, 1, 2, or 4)
    """
    type_chart = load_type_chart()

    if attack_type.lower() not in type_chart:
        return 1.0

    multiplier = 1.0
    for def_type in defending_types:
        if def_type:
            effectiveness = type_chart[attack_type.lower()].get(def_type.lower(), 1.0)
            multiplier *= effectiveness

    return multiplier
