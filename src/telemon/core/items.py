"""Centralized item catalog for all items in Telemon.

All item definitions live here. Both the seed script and runtime code
import from this module so there is a single source of truth.
"""

from typing import Any


# ──────────────────────────────────────────────
# Item definitions
# ──────────────────────────────────────────────

ALL_ITEMS: list[dict[str, Any]] = [
    # ── Evolution Stones (IDs 1–10, 500 TC) ──
    {"id": 1,  "name": "Fire Stone",    "name_lower": "fire stone",    "category": "evolution", "cost": 500,  "sell_price": 250,  "is_consumable": True,  "is_holdable": False, "description": "Evolves certain Fire-type Pokemon."},
    {"id": 2,  "name": "Water Stone",   "name_lower": "water stone",   "category": "evolution", "cost": 500,  "sell_price": 250,  "is_consumable": True,  "is_holdable": False, "description": "Evolves certain Water-type Pokemon."},
    {"id": 3,  "name": "Thunder Stone", "name_lower": "thunder stone", "category": "evolution", "cost": 500,  "sell_price": 250,  "is_consumable": True,  "is_holdable": False, "description": "Evolves certain Electric-type Pokemon."},
    {"id": 4,  "name": "Leaf Stone",    "name_lower": "leaf stone",    "category": "evolution", "cost": 500,  "sell_price": 250,  "is_consumable": True,  "is_holdable": False, "description": "Evolves certain Grass-type Pokemon."},
    {"id": 5,  "name": "Moon Stone",    "name_lower": "moon stone",    "category": "evolution", "cost": 500,  "sell_price": 250,  "is_consumable": True,  "is_holdable": False, "description": "Evolves certain Fairy/Normal Pokemon."},
    {"id": 6,  "name": "Sun Stone",     "name_lower": "sun stone",     "category": "evolution", "cost": 500,  "sell_price": 250,  "is_consumable": True,  "is_holdable": False, "description": "Evolves certain Grass-type Pokemon."},
    {"id": 7,  "name": "Dusk Stone",    "name_lower": "dusk stone",    "category": "evolution", "cost": 500,  "sell_price": 250,  "is_consumable": True,  "is_holdable": False, "description": "Evolves certain Ghost/Dark Pokemon."},
    {"id": 8,  "name": "Dawn Stone",    "name_lower": "dawn stone",    "category": "evolution", "cost": 500,  "sell_price": 250,  "is_consumable": True,  "is_holdable": False, "description": "Evolves certain gendered Pokemon."},
    {"id": 9,  "name": "Shiny Stone",   "name_lower": "shiny stone",   "category": "evolution", "cost": 500,  "sell_price": 250,  "is_consumable": True,  "is_holdable": False, "description": "Evolves certain Pokemon with a brilliant sheen."},
    {"id": 10, "name": "Ice Stone",     "name_lower": "ice stone",     "category": "evolution", "cost": 500,  "sell_price": 250,  "is_consumable": True,  "is_holdable": False, "description": "Evolves certain Ice-type Pokemon."},

    # ── Trade Evolution Items (IDs 11–21, 1000–1500 TC) ──
    {"id": 11, "name": "Metal Coat",    "name_lower": "metal coat",    "category": "evolution", "cost": 1000, "sell_price": 500,  "is_consumable": True,  "is_holdable": False, "description": "Evolves Onix into Steelix, Scyther into Scizor."},
    {"id": 12, "name": "King's Rock",   "name_lower": "king's rock",   "category": "evolution", "cost": 1000, "sell_price": 500,  "is_consumable": True,  "is_holdable": False, "description": "A rock crown used in certain evolutions."},
    {"id": 13, "name": "Up-Grade",      "name_lower": "up grade",      "category": "evolution", "cost": 1500, "sell_price": 750,  "is_consumable": True,  "is_holdable": False, "description": "Evolves Porygon into Porygon2."},
    {"id": 14, "name": "Dubious Disc",  "name_lower": "dubious disc",  "category": "evolution", "cost": 1500, "sell_price": 750,  "is_consumable": True,  "is_holdable": False, "description": "Evolves Porygon2 into Porygon-Z."},
    {"id": 15, "name": "Reaper Cloth",  "name_lower": "reaper cloth",  "category": "evolution", "cost": 1500, "sell_price": 750,  "is_consumable": True,  "is_holdable": False, "description": "Evolves Dusclops into Dusknoir."},
    {"id": 16, "name": "Deep Sea Tooth","name_lower": "deep sea tooth", "category": "evolution", "cost": 1000, "sell_price": 500,  "is_consumable": True,  "is_holdable": False, "description": "Evolves Clamperl into Huntail."},
    {"id": 17, "name": "Deep Sea Scale","name_lower": "deep sea scale", "category": "evolution", "cost": 1000, "sell_price": 500,  "is_consumable": True,  "is_holdable": False, "description": "Evolves Clamperl into Gorebyss."},
    {"id": 18, "name": "Magmarizer",    "name_lower": "magmarizer",    "category": "evolution", "cost": 1500, "sell_price": 750,  "is_consumable": True,  "is_holdable": False, "description": "Evolves Magmar into Magmortar."},
    {"id": 19, "name": "Electirizer",   "name_lower": "electirizer",   "category": "evolution", "cost": 1500, "sell_price": 750,  "is_consumable": True,  "is_holdable": False, "description": "Evolves Electabuzz into Electivire."},
    {"id": 20, "name": "Sachet",        "name_lower": "sachet",        "category": "evolution", "cost": 1000, "sell_price": 500,  "is_consumable": True,  "is_holdable": False, "description": "Evolves Spritzee into Aromatisse."},
    {"id": 21, "name": "Whipped Dream", "name_lower": "whipped dream", "category": "evolution", "cost": 1000, "sell_price": 500,  "is_consumable": True,  "is_holdable": False, "description": "Evolves Swirlix into Slurpuff."},

    # ── Unique Evolution Items (IDs 22–28, 500–1500 TC) ──
    {"id": 22, "name": "Black Augurite",   "name_lower": "black augurite",   "category": "evolution", "cost": 1500, "sell_price": 750,  "is_consumable": True,  "is_holdable": False, "description": "Evolves Scyther into Kleavor."},
    {"id": 23, "name": "Peat Block",       "name_lower": "peat block",       "category": "evolution", "cost": 1500, "sell_price": 750,  "is_consumable": True,  "is_holdable": False, "description": "Evolves Ursaring into Ursaluna."},
    {"id": 24, "name": "Cracked Pot",      "name_lower": "cracked pot",      "category": "evolution", "cost": 500,  "sell_price": 250,  "is_consumable": True,  "is_holdable": False, "description": "Evolves Sinistea into Polteageist."},
    {"id": 25, "name": "Sweet Apple",      "name_lower": "sweet apple",      "category": "evolution", "cost": 500,  "sell_price": 250,  "is_consumable": True,  "is_holdable": False, "description": "Evolves Applin into Appletun."},
    {"id": 26, "name": "Tart Apple",       "name_lower": "tart apple",       "category": "evolution", "cost": 500,  "sell_price": 250,  "is_consumable": True,  "is_holdable": False, "description": "Evolves Applin into Flapple."},
    {"id": 27, "name": "Auspicious Armor", "name_lower": "auspicious armor", "category": "evolution", "cost": 1500, "sell_price": 750,  "is_consumable": True,  "is_holdable": False, "description": "Evolves Charcadet into Armarouge."},
    {"id": 28, "name": "Malicious Armor",  "name_lower": "malicious armor",  "category": "evolution", "cost": 1500, "sell_price": 750,  "is_consumable": True,  "is_holdable": False, "description": "Evolves Charcadet into Ceruledge."},

    # ── Trade Helper (ID 29) ──
    {"id": 29, "name": "Linking Cord",  "name_lower": "linking cord",  "category": "evolution", "cost": 3000, "sell_price": 1500, "is_consumable": True,  "is_holdable": False, "description": "Simulates a trade. Evolves trade-evolution Pokemon without trading."},

    # ── Friendship (ID 30) ──
    {"id": 30, "name": "Soothe Bell",   "name_lower": "soothe bell",   "category": "utility",  "cost": 2000, "sell_price": 1000, "is_consumable": False, "is_holdable": True,  "description": "Doubles friendship gains when held by a Pokemon."},

    # ── Battle Items (IDs 101–108) ──
    {"id": 101, "name": "Leftovers",    "name_lower": "leftovers",     "category": "battle", "cost": 1000, "sell_price": 500,  "is_consumable": False, "is_holdable": True,  "description": "Restores a little HP each turn in battle."},
    {"id": 102, "name": "Choice Band",  "name_lower": "choice band",   "category": "battle", "cost": 1500, "sell_price": 750,  "is_consumable": False, "is_holdable": True,  "description": "Boosts Attack but locks into one move."},
    {"id": 103, "name": "Choice Specs", "name_lower": "choice specs",  "category": "battle", "cost": 1500, "sell_price": 750,  "is_consumable": False, "is_holdable": True,  "description": "Boosts Sp. Attack but locks into one move."},
    {"id": 104, "name": "Choice Scarf", "name_lower": "choice scarf",  "category": "battle", "cost": 1500, "sell_price": 750,  "is_consumable": False, "is_holdable": True,  "description": "Boosts Speed but locks into one move."},
    {"id": 105, "name": "Life Orb",     "name_lower": "life orb",      "category": "battle", "cost": 2000, "sell_price": 1000, "is_consumable": False, "is_holdable": True,  "description": "Boosts all damage but costs HP each attack."},
    {"id": 106, "name": "Focus Sash",   "name_lower": "focus sash",    "category": "battle", "cost": 1000, "sell_price": 500,  "is_consumable": False, "is_holdable": True,  "description": "Survives a one-hit KO with 1 HP (once)."},
    {"id": 107, "name": "Assault Vest", "name_lower": "assault vest",  "category": "battle", "cost": 1500, "sell_price": 750,  "is_consumable": False, "is_holdable": True,  "description": "Boosts Sp. Defense but disables status moves."},
    {"id": 108, "name": "Rocky Helmet", "name_lower": "rocky helmet",  "category": "battle", "cost": 1000, "sell_price": 500,  "is_consumable": False, "is_holdable": True,  "description": "Damages attackers that make contact."},

    # ── Utility Items (IDs 201–203) ──
    {"id": 201, "name": "Rare Candy",   "name_lower": "rare candy",    "category": "utility", "cost": 200,  "sell_price": 100,  "is_consumable": True,  "is_holdable": False, "description": "Raises a Pokemon's level by 1."},
    {"id": 202, "name": "Incense",      "name_lower": "incense",       "category": "utility", "cost": 500,  "sell_price": 250,  "is_consumable": True,  "is_holdable": False, "description": "Spawns Pokemon in DMs for 1 hour. (Coming soon)"},
    {"id": 203, "name": "XP Boost",     "name_lower": "xp boost",      "category": "utility", "cost": 300,  "sell_price": 150,  "is_consumable": True,  "is_holdable": False, "description": "Earn 2x XP for 1 hour. (Coming soon)"},

    # ── Special Items (IDs 301–302) ──
    {"id": 301, "name": "Shiny Charm",  "name_lower": "shiny charm",   "category": "special", "cost": 50000,  "sell_price": 25000, "is_consumable": False, "is_holdable": False, "description": "Triples your shiny odds! A must-have for shiny hunters."},
    {"id": 302, "name": "Oval Charm",   "name_lower": "oval charm",    "category": "special", "cost": 25000,  "sell_price": 12500, "is_consumable": False, "is_holdable": False, "description": "Increases egg hatch speed. (Coming soon)"},
]


# ──────────────────────────────────────────────
# Lookup dictionaries (built once at import)
# ──────────────────────────────────────────────

ITEM_BY_NAME: dict[str, dict[str, Any]] = {
    item["name_lower"]: item for item in ALL_ITEMS
}

ITEM_BY_ID: dict[int, dict[str, Any]] = {
    item["id"]: item for item in ALL_ITEMS
}


# ──────────────────────────────────────────────
# Category helpers
# ──────────────────────────────────────────────

EVOLUTION_ITEM_IDS = {item["id"] for item in ALL_ITEMS if item["category"] == "evolution"}
BATTLE_ITEM_IDS = {item["id"] for item in ALL_ITEMS if item["category"] == "battle"}
UTILITY_ITEM_IDS = {item["id"] for item in ALL_ITEMS if item["category"] == "utility"}
SPECIAL_ITEM_IDS = {item["id"] for item in ALL_ITEMS if item["category"] == "special"}

# Linking Cord ID for convenience
LINKING_CORD_ID = 29
SOOTHE_BELL_ID = 30
RARE_CANDY_ID = 201
