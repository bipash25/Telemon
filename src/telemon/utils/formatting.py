"""Formatting utilities for display."""


def format_iv_bar(iv: int, max_iv: int = 31) -> str:
    """Format an IV value as a visual bar.

    Args:
        iv: The IV value (0-31)
        max_iv: Maximum IV value

    Returns:
        A string representing the IV as a progress bar
    """
    filled = int((iv / max_iv) * 10)
    empty = 10 - filled
    return "" * filled + "" * empty


def format_pokemon_summary(
    name: str,
    level: int,
    iv_percentage: float,
    is_shiny: bool = False,
    is_favorite: bool = False,
) -> str:
    """Format a Pokemon summary line.

    Args:
        name: Pokemon name
        level: Pokemon level
        iv_percentage: IV percentage
        is_shiny: Whether the Pokemon is shiny
        is_favorite: Whether the Pokemon is a favorite

    Returns:
        Formatted summary string
    """
    shiny = "" if is_shiny else ""
    fav = "" if is_favorite else ""
    return f"{shiny}{fav}<b>{name}</b> Lv.{level} | {iv_percentage:.1f}% IV"


def format_hp_bar(current: int, max_hp: int, width: int = 10) -> str:
    """Format HP as a visual bar.

    Args:
        current: Current HP
        max_hp: Maximum HP
        width: Bar width in characters

    Returns:
        HP bar string
    """
    if max_hp == 0:
        return "" * width

    ratio = current / max_hp
    filled = int(ratio * width)

    # Color based on HP percentage
    if ratio > 0.5:
        bar_char = ""  # Green
    elif ratio > 0.2:
        bar_char = ""  # Yellow
    else:
        bar_char = ""  # Red

    empty_char = ""

    return bar_char * filled + empty_char * (width - filled)


def format_type_badge(type_name: str) -> str:
    """Format a type as an emoji badge.

    Args:
        type_name: The type name

    Returns:
        Emoji representation of the type
    """
    type_emojis = {
        "normal": "",
        "fire": "",
        "water": "",
        "electric": "",
        "grass": "",
        "ice": "",
        "fighting": "",
        "poison": "",
        "ground": "",
        "flying": "",
        "psychic": "",
        "bug": "",
        "rock": "",
        "ghost": "",
        "dragon": "",
        "dark": "",
        "steel": "",
        "fairy": "",
    }
    return type_emojis.get(type_name.lower(), "")


def format_rarity_badge(rarity: str) -> str:
    """Format rarity as a badge.

    Args:
        rarity: The rarity level

    Returns:
        Colored rarity badge
    """
    badges = {
        "common": "",
        "uncommon": "",
        "rare": "",
        "ultra_rare": "",
        "legendary": "",
        "mythical": "",
    }
    return badges.get(rarity.lower(), "")
