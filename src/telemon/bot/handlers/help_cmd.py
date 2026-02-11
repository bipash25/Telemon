"""Help command handlers."""

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

router = Router(name="help")


HELP_MESSAGE = """
<b>Telemon Commands</b>

<b>Getting Started</b>
/start - Start the bot, pick a starter
/help - Show this help message
/help [command] - Detailed help for a command

<b>Profile & Economy</b>
/profile - View your trainer profile
/balance - Check your Telecoins
/daily - Claim daily reward (+friendship)
/gift @user [amount] - Send Telecoins

<b>Catching & Collection</b>
/catch [name] - Catch a wild Pokemon
/hint - Get a hint for the current spawn
/pokemon - List your Pokemon (filters: shiny, type:fire, gen:3, sort:iv)
/info [#] - View Pokemon details
/select [#] - Select active Pokemon
/nickname [name] - Rename selected Pokemon
/favorite [#] - Toggle favorite
/release [#] - Release a Pokemon
/release duplicates - Bulk release duplicate Pokemon
/release all [filters] - Bulk release with filters

<b>Evolution & Training</b>
/evolve [#] [item] - Evolve a Pokemon
/pet [#] - Increase friendship (+5, doubled with Soothe Bell)

<b>Battle</b>
/duel @user - Challenge to PvP battle
/battle wild - Fight a random wild Pokemon
/battle npc - List NPC trainers (gym leaders)
/battle npc [name] - Fight a specific trainer

<b>Trading</b>
/trade @user - Start a trade
/trade add/remove/confirm/cancel

<b>Market</b>
/market - Browse marketplace
/market sell [#] [price] - List for sale
/market buy [id] - Buy a listing

<b>Shop & Items</b>
/shop - View the shop (evolution items, battle items, etc.)
/buy [id] [qty] - Purchase an item
/use [id] [#] - Use an item on a Pokemon
/inventory - View your items
/shopinfo [id] - Item details

<b>Quests</b>
/quest - View daily & weekly quests
/quest claimall - Claim completed quest rewards

<b>Wonder Trade</b>
/wt [pokemon#] - Deposit for random swap
/wt status - Check pool status

<b>Pokedex & Hunting</b>
/pokedex - Pokedex overview (with gen breakdown)
/pokedex list gen:3 - Browse by generation
/pokedex caught/missing/shiny
/shinyhunt [name] - Set shiny target
/hunt status/stop/odds

<b>Leaderboards</b>
/leaderboard - View rankings
/lb catches/wealth/pokedex/shiny/battles/rating/group
/rank - Your ranking

<b>Achievements</b>
/achievements - View your achievement progress
/badges - Same as /achievements

<b>Admin</b> (Group admins only)
/settings - Group settings
/spawn - Force a spawn
/addspawner @user - Grant spawn permissions
/removespawner @user - Remove permissions

<i>Most commands work with index numbers (/info 3) or selected Pokemon (/info)</i>
"""


COMMAND_HELP = {
    "catch": """
<b>/catch [pokemon_name]</b>
Also: /c

Catch a wild Pokemon that has spawned in the chat.
You must type the correct name of the Pokemon.

<b>Example:</b> /catch pikachu
""",
    "pokemon": """
<b>/pokemon</b>
Also: /p

View your Pokemon collection with filters and sorting.

<b>Filters (both styles work):</b>
shiny or --shiny — Show only shinies
legendary or --legendary — Show legendaries
name:char or --name char — Search by name
type:fire or --type fire — Filter by type
gen:3 or --gen 3 — Filter by generation
fav or --favorites — Show only favorites

<b>Sorting:</b>
sort:iv — Sort by IV percentage
sort:level — Sort by level
sort:dex — Sort by Pokedex number
sort:name — Sort alphabetically

<b>Example:</b> /pokemon shiny type:fire sort:iv
<b>Example:</b> /pokemon gen:1 sort:dex
""",
    "evolve": """
<b>/evolve [#] [item name]</b>

Evolve a Pokemon. Works with index number or selected Pokemon.

<b>Evolution Types:</b>
Level-up: Just reach the required level, then /evolve
Item: /evolve 1 fire stone (uses and consumes the item)
Trade: /evolve 1 linking cord (uses Linking Cord from shop)
Friendship: Raise friendship to 220+ with /pet, then /evolve

<b>Example:</b> /evolve 1
<b>Example:</b> /evolve 1 thunder stone
<b>Example:</b> /evolve linking cord (on selected Pokemon)
""",
    "trade": """
<b>/trade @user</b>

Start a trade with another user.

<b>Trade Commands:</b>
/trade add [#] — Add Pokemon
/trade add coins [amount] — Add Telecoins
/trade remove [#] — Remove Pokemon
/trade confirm — Confirm your side
/trade cancel — Cancel the trade

Both users must confirm for trade to complete.
Trade evolutions trigger automatically!
""",
    "market": """
<b>/market search [filters]</b>

Browse the global Pokemon marketplace.

<b>Filters:</b>
--name [text] — Search by name
--type [type] — Filter by type
--shiny — Shinies only
--legendary — Legendaries only
--iv [min]-[max] — IV percentage range
--level [min]-[max] — Level range
--price [min]-[max] — Price range

<b>Example:</b> /market search --name charizard --shiny
""",
    "quest": """
<b>/quest</b>
Also: /quests, /q

View and manage your daily & weekly quests.

<b>Commands:</b>
/quest — View all active quests with progress
/quest claimall — Claim all completed quest rewards
/quest help — Detailed quest information

<b>Quest Types:</b>
- Catch Pokemon (general or by type)
- Win battles, evolve, trade, pet
- Sell on market, use items, claim daily

Daily quests (3) reset at midnight UTC.
Weekly quests (2) reset Monday midnight UTC.
""",
    "shop": """
<b>/shop</b>

Browse the item shop.

<b>Item Categories:</b>
Evolution Stones (500 TC) — Fire, Water, Thunder, etc.
Evolution Items (1000-1500 TC) — Metal Coat, Dubious Disc, etc.
Linking Cord (3000 TC) — Evolve trade Pokemon without trading!
Soothe Bell (2000 TC) — Doubles friendship gains
Battle Items — Leftovers, Choice Band, Life Orb, etc.
Utility — Rare Candy (200 TC), Incense, XP Boost
Special — Shiny Charm (50,000 TC), Oval Charm

/buy [id] [qty] — Purchase items
/shopinfo [id] — View item details
/use [id] [#] — Use item on Pokemon
""",
    "gift": """
<b>/gift @user [amount]</b>
Also: /give, /send

Send Telecoins to another trainer.

<b>Usage:</b>
/gift @friend 500 — Send 500 TC to @friend
Reply to a message + /gift 500 — Send to that user

Maximum: 1,000,000 TC per transfer.
""",
    "pet": """
<b>/pet [#]</b>

Pet your Pokemon to increase its friendship.

Base gain: +5 friendship per pet
With Soothe Bell: +10 friendship per pet

Friendship is needed for certain evolutions (Eevee -> Espeon, Riolu -> Lucario, etc.)
Max friendship: 255

<b>Other friendship sources:</b>
/daily — +5 to selected Pokemon
Catching Pokemon — +1 to selected Pokemon  
Rare Candy — +3 per use
""",
    "wondertrade": """
<b>/wt [pokemon#]</b>
Also: /wondertrade

Deposit a Pokemon and receive a random one from another trainer!

<b>Commands:</b>
/wt [pokemon#] — Deposit a Pokemon for trade
/wt status — Check pool status & your pending trade
/wt help — Detailed help

<b>How it works:</b>
1. Use /wt [number] to deposit a Pokemon
2. If someone is waiting, you swap instantly!
3. If not, your Pokemon waits for the next trader

<b>Rules:</b>
- 1 Pokemon in the pool at a time
- Favorites & selected Pokemon can't be traded
- 5 minute cooldown between trades
""",
    "achievements": """
<b>/achievements</b>
Also: /badges, /ach

View your achievement progress across all categories.

<b>Categories:</b>
Catching — Catch milestones (1, 10, 50, 100, 500, 1000)
Shiny — Shiny catch milestones (1, 10, 50)
Pokedex — Species registration milestones (10, 50, 151, 500, 1025)
Evolution — Evolution milestones (1, 10, 50)
Battle — Battle win milestones (1, 10, 50, 100)
Trading — Trade milestones (1, 10, 50)
Daily Streak — Streak milestones (3, 7, 14, 30 days)
Special — Perfect IV, Legendary, Mythical catches
Wonder Trade — Wonder Trade milestones (10)

Each achievement grants a TC reward when unlocked.
""",
    "battle": """
<b>/battle</b>
Also: /duel

Battle other trainers or fight wild Pokemon and NPC trainers!

<b>PvP:</b>
/duel @username — Challenge a player to a 1v1 battle

<b>PvE - Wild:</b>
/battle wild — Fight a random wild Pokemon
Earn XP and Telecoins. Wild level matches yours (+-5).

<b>PvE - NPC Trainers:</b>
/battle npc — List all available NPC trainers
/battle npc brock — Fight Gym Leader Brock
/battle npc lance — Fight Elite Four Lance
/battle npc red — Fight Champion Red

NPC trainers scale with your level and give bonus rewards.
Higher difficulty trainers give bigger multipliers!

<b>During Battle:</b>
Select moves with inline buttons
Type effectiveness, stats, STAB all apply
/forfeit — End battle early
""",
}


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    """Handle /help command."""
    args = message.text.split() if message.text else []

    if len(args) > 1:
        # Help for specific command
        command = args[1].lower().lstrip("/")
        if command in COMMAND_HELP:
            await message.answer(COMMAND_HELP[command])
            return

    await message.answer(HELP_MESSAGE)
