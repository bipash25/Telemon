"""Pokemon sprite emoji helper — loads emoji_map.json and provides inline emoji tags.

Usage:
    from telemon.core.emoji import poke_emoji

    # Returns '<tg-emoji emoji-id="123456">🔴</tg-emoji>' or fallback ''
    emoji_tag = poke_emoji(25)  # Pikachu
"""

from __future__ import annotations

import json
from pathlib import Path

_EMOJI_MAP: dict[str, str] = {}
_LOADED = False


def _load_map() -> None:
    global _EMOJI_MAP, _LOADED
    if _LOADED:
        return
    map_path = Path(__file__).parent.parent.parent.parent / "data" / "emoji_map.json"
    if map_path.exists():
        try:
            _EMOJI_MAP = json.loads(map_path.read_text())
        except Exception:
            _EMOJI_MAP = {}
    _LOADED = True


def reload_emoji_map() -> int:
    """Force reload the emoji map. Returns count of loaded emoji."""
    global _LOADED
    _LOADED = False
    _load_map()
    return len(_EMOJI_MAP)


def poke_emoji(dex_number: int, fallback: str = "") -> str:
    """Get an inline custom emoji tag for a Pokemon species.

    Returns HTML like:  <tg-emoji emoji-id="12345">🔴</tg-emoji>
    If no emoji is mapped, returns the fallback string.
    """
    _load_map()
    emoji_id = _EMOJI_MAP.get(str(dex_number))
    if not emoji_id:
        return fallback
    return f'<tg-emoji emoji-id="{emoji_id}">\U0001f534</tg-emoji>'


def has_emoji(dex_number: int) -> bool:
    """Check if we have a custom emoji for this species."""
    _load_map()
    return str(dex_number) in _EMOJI_MAP


def emoji_count() -> int:
    """Return how many emoji are loaded."""
    _load_map()
    return len(_EMOJI_MAP)
