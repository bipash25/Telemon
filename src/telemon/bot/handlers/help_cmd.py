"""Help command handlers."""

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

router = Router(name="help")


HELP_MESSAGE = """
<b>Telemon Commands</b>

<b>General</b>
/start - Start the bot
/help - Show this help message
/profile - View your trainer profile
/balance - Check your Telecoins
/daily - Claim daily reward

<b>Pokemon</b>
/catch &lt;name&gt; - Catch a wild Pokemon
/c &lt;name&gt; - Short for /catch
/hint - Get a hint for the current spawn
/pokemon - List your Pokemon
/p - Short for /pokemon
/info [id] - View Pokemon details
/select &lt;id&gt; - Select active Pokemon
/nickname &lt;id&gt; &lt;name&gt; - Rename Pokemon
/release &lt;id&gt; - Release a Pokemon
/favorite &lt;id&gt; - Toggle favorite

<b>Training</b>
/moves [id] - View Pokemon moves
/learn &lt;move&gt; - Learn a new move
/evolve [id] - Evolve your Pokemon
/train - Train active Pokemon

<b>Battle</b>
/duel @user - Challenge to battle

<b>Trading</b>
/trade @user - Start a trade
/trade add &lt;id&gt; - Add Pokemon to trade
/trade confirm - Confirm trade
/trade cancel - Cancel trade

<b>Market</b>
/market search - Browse marketplace
/market buy &lt;id&gt; - Buy a listing
/market sell &lt;id&gt; &lt;price&gt; - List for sale

<b>Shop</b>
/shop - View the shop
/buy &lt;item&gt; - Purchase an item
/inventory - View your items

<b>Hunting</b>
/shinyhunt &lt;name&gt; - Set shiny target
/pokedex - View Pokedex progress

<b>Admin</b> (Group admins only)
/settings - Group settings
/spawn - Force a spawn

<i>Tip: Most commands work in both groups and DMs!</i>
"""


COMMAND_HELP = {
    "catch": """
<b>/catch &lt;pokemon_name&gt;</b>
Also: /c

Catch a wild Pokemon that has spawned in the chat.
You must type the correct name of the Pokemon.

<b>Example:</b> /catch pikachu
""",
    "pokemon": """
<b>/pokemon</b>
Also: /p

View your Pokemon collection with filters and sorting.

<b>Filters:</b>
--shiny - Show only shinies
--legendary - Show legendaries
--name &lt;text&gt; - Search by name
--type &lt;type&gt; - Filter by type

<b>Sorting:</b>
--order iv - Sort by IV percentage
--order level - Sort by level
--order recent - Sort by catch date

<b>Example:</b> /pokemon --shiny --order iv
""",
    "trade": """
<b>/trade @user</b>

Start a trade with another user.

<b>Trade Commands:</b>
/trade add &lt;pokemon_id&gt; - Add Pokemon
/trade add coins &lt;amount&gt; - Add Telecoins
/trade remove &lt;id&gt; - Remove Pokemon
/trade confirm - Confirm your side
/trade cancel - Cancel the trade

Both users must confirm for trade to complete.
""",
    "market": """
<b>/market search [filters]</b>

Browse the global Pokemon marketplace.

<b>Filters:</b>
--name &lt;text&gt; - Search by name
--type &lt;type&gt; - Filter by type
--shiny - Shinies only
--legendary - Legendaries only
--iv &lt;min&gt;-&lt;max&gt; - IV percentage range
--level &lt;min&gt;-&lt;max&gt; - Level range
--price &lt;min&gt;-&lt;max&gt; - Price range

<b>Example:</b> /market search --name charizard --shiny
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
