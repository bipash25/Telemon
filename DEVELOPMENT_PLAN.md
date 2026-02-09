# Telemon - Complete Development Plan

> A Pokemon-style game bot for Telegram, inspired by Poketwo (Discord)

## Project Overview

| Attribute | Value |
|-----------|-------|
| **Name** | Telemon |
| **Type** | Pokemon-style Telegram Bot Game |
| **Stack** | Python 3.11+ \| aiogram 3.x \| PostgreSQL \| Redis |
| **Currency** | Telecoins |
| **Scope** | 1000+ Pokemon (All Generations), Advanced Competitive Battles |
| **Target Scale** | Medium (10-100 groups) |

---

## Architecture Overview

```
telemon/
├── bot/                      # Telegram bot logic
│   ├── handlers/             # Command and callback handlers
│   │   ├── __init__.py
│   │   ├── start.py          # /start, /help commands
│   │   ├── catch.py          # /catch, /hint commands
│   │   ├── pokemon.py        # /pokemon, /info, /select
│   │   ├── battle.py         # /duel, battle callbacks
│   │   ├── trade.py          # /trade commands
│   │   ├── market.py         # /market commands
│   │   ├── shop.py           # /shop, /buy, /inventory
│   │   ├── profile.py        # /profile, /balance, /daily
│   │   └── admin.py          # /settings, /spawn (admin)
│   ├── keyboards/            # Inline keyboard builders
│   │   ├── __init__.py
│   │   ├── pokemon_list.py
│   │   ├── battle_ui.py
│   │   ├── trade_ui.py
│   │   └── market_ui.py
│   ├── middlewares/          # Rate limiting, user loading
│   │   ├── __init__.py
│   │   ├── auth.py           # User registration/loading
│   │   ├── throttle.py       # Rate limiting
│   │   └── logging.py        # Request logging
│   ├── states/               # FSM states
│   │   ├── __init__.py
│   │   ├── battle.py
│   │   └── trade.py
│   └── filters/              # Custom filters
│       └── __init__.py
├── core/                     # Business logic
│   ├── __init__.py
│   ├── spawning/             # Spawn engine
│   │   ├── __init__.py
│   │   ├── engine.py         # Spawn logic
│   │   └── scheduler.py      # Time-based spawns
│   ├── catching/             # Catch mechanics
│   │   ├── __init__.py
│   │   └── catcher.py
│   ├── battle/               # Battle engine
│   │   ├── __init__.py
│   │   ├── engine.py         # Main battle logic
│   │   ├── damage.py         # Damage calculation
│   │   ├── effects.py        # Status effects, weather
│   │   ├── moves.py          # Move execution
│   │   └── ai.py             # NPC AI (future)
│   ├── trading/              # Trade system
│   │   ├── __init__.py
│   │   └── trade_session.py
│   ├── market/               # Marketplace
│   │   ├── __init__.py
│   │   └── listings.py
│   ├── evolution/            # Evolution/leveling
│   │   ├── __init__.py
│   │   ├── evolution.py
│   │   └── experience.py
│   └── economy/              # Currency system
│       ├── __init__.py
│       └── transactions.py
├── database/                 # Database layer
│   ├── __init__.py
│   ├── session.py            # Async session management
│   ├── models/               # SQLAlchemy models
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── pokemon.py
│   │   ├── species.py
│   │   ├── move.py
│   │   ├── item.py
│   │   ├── group.py
│   │   ├── trade.py
│   │   ├── market.py
│   │   └── battle.py
│   ├── repositories/         # Data access patterns
│   │   ├── __init__.py
│   │   ├── user_repo.py
│   │   ├── pokemon_repo.py
│   │   └── market_repo.py
│   └── migrations/           # Alembic migrations
│       └── versions/
├── data/                     # Static Pokemon data
│   ├── pokemon.json          # All Pokemon species
│   ├── moves.json            # All moves
│   ├── abilities.json        # All abilities
│   ├── items.json            # All items
│   ├── natures.json          # 25 natures
│   ├── type_chart.json       # Type effectiveness
│   └── evolution_chains.json # Evolution data
├── scripts/                  # Utility scripts
│   ├── import_pokemon_data.py
│   └── seed_database.py
├── utils/                    # Shared utilities
│   ├── __init__.py
│   ├── formatting.py         # Message formatting
│   ├── pagination.py         # List pagination
│   ├── fuzzy_match.py        # Pokemon name matching
│   └── calculations.py       # Stat calculations
├── config/                   # Configuration
│   ├── __init__.py
│   └── settings.py           # Pydantic settings
├── tests/                    # Test suite
│   ├── __init__.py
│   ├── test_battle.py
│   ├── test_catching.py
│   └── test_trading.py
├── .env.example              # Environment template
├── .gitignore
├── pyproject.toml            # Project dependencies
├── docker-compose.yml        # Local development
├── Dockerfile
├── alembic.ini               # Migration config
├── main.py                   # Entry point
└── README.md
```

---

## Core Features

### 1. Wild Pokemon Spawning (Hybrid System)

**Triggers:**
- **Message-based:** Every N messages in a group (configurable, default: 50)
- **Time-based:** Random spawn every X minutes if chat has activity
- **Guaranteed:** At least 1 spawn per hour in active chats

**Mechanics:**
- Pokemon appear with image (silhouette or full sprite)
- No name shown - users must identify and catch
- Spawn timeout: Pokemon flees after 2 minutes
- Weighted rarity system (common → legendary)
- Time-of-day spawns (Hoothoot at night, etc.)
- Shiny chance: 1/4096 (base rate)

### 2. Catching System

**Commands:**
- `/catch <name>` or `/c <name>` - Attempt to catch
- `/hint` - Reveal letters progressively (costs Telecoins)

**On Catch:**
- Generate random IVs (0-31 per stat)
- Assign random nature (25 options)
- Pick random ability from species pool
- Roll for shiny (1/4096 base)
- Award Telecoins (10-100 based on rarity)
- XP to active Pokemon

### 3. Pokemon Collection (PC)

**Commands:**
- `/pokemon` or `/p` - List Pokemon (paginated)
  - Filters: `--shiny`, `--legendary`, `--name "char"`, `--type fire`
  - Sorting: `--order iv`, `--order level`, `--order recent`
- `/select <id>` - Set active/lead Pokemon
- `/info [id]` - Detailed stats view
- `/nickname <id> <name>` - Rename Pokemon
- `/release <id>` - Release with confirmation
- `/favorite <id>` - Protect from accidental release

### 4. Leveling & Experience

**XP Sources:**
| Activity | XP Gained |
|----------|-----------|
| Catching Pokemon | 50-200 (by rarity) |
| Winning battles | 100-500 |
| Training (`/train`) | 50-100 (cooldown) |
| Daily bonus | 100 |

**Formula:** `XP_needed = level^3` (Pokemon-style curve)

### 5. Evolution System

**Types Supported:**
- Level-based (Charmander → Charmeleon at L16)
- Item-based (Fire Stone on Eevee → Flareon)
- Trade-based (Haunter → Gengar when traded)
- Friendship-based (Eevee → Espeon/Umbreon)
- Time-based (day/night evolutions)
- Special conditions (Inkay needs "held upside down")

**Commands:**
- `/evolve <id>` - Evolve with item
- `/evolve <id> cancel` - Cancel pending evolution

### 6. Moves & Learnsets

**Commands:**
- `/moves [id]` - View current 4 moves
- `/learn <move>` - Learn new move (if eligible)
- `/moveinfo <move>` - Move details
- `/forget <slot>` - Forget a move

**Move Categories:**
- Physical (uses Attack/Defense)
- Special (uses Sp.Atk/Sp.Def)
- Status (no damage, effects only)

### 7. Battle System (Advanced Competitive)

**Features:**
- Turn-based combat with move selection
- Full 18-type effectiveness chart
- Physical/Special split
- STAB (1.5x same-type bonus)
- Critical hits (1.5x, varies by move)
- Accuracy/Evasion stages
- Status conditions:
  - Burn (halves Attack, chip damage)
  - Poison/Toxic (chip damage, Toxic escalates)
  - Paralysis (25% skip turn, halves Speed)
  - Sleep (1-3 turns, can't move)
  - Freeze (can't move, thaws randomly)
- Weather: Sun, Rain, Sand, Hail, Snow
- Entry hazards: Stealth Rock, Spikes, Toxic Spikes
- Stat stages (-6 to +6)
- 300+ Abilities (passive effects)
- Held items in battle
- Priority brackets (-7 to +5)
- Switching Pokemon mid-battle

**Commands:**
- `/duel @user` - Challenge to battle
- Battle uses inline keyboard for move selection

**Battle UI Example:**
```
🔴 Charizard Lv.50        [Opponent]
HP: ████████░░ 80%
Status: None

🔵 Blastoise Lv.48        [You]
HP: ██████████ 100%  
Status: None

┌─────────────┬─────────────┐
│ Hydro Pump  │ Ice Beam    │
├─────────────┼─────────────┤
│ Rapid Spin  │ Protect     │
├─────────────┼─────────────┤
│ Switch      │ Forfeit     │
└─────────────┴─────────────┘
```

### 8. Trading System

**Commands:**
- `/trade @user` - Start trade session
- `/trade add <pokemon_id>` - Add Pokemon to trade
- `/trade add coins <amount>` - Add Telecoins
- `/trade remove <pokemon_id>` - Remove Pokemon
- `/trade confirm` - Confirm (both must confirm)
- `/trade cancel` - Cancel trade

**Features:**
- Real-time trade UI with inline keyboards
- Both sides visible
- Trade evolution triggers automatically
- Trade history logging

### 9. Global Marketplace

**Commands:**
- `/market search [filters]` - Browse listings
  - `--name "Charizard"`
  - `--type fire`
  - `--shiny`
  - `--legendary`
  - `--iv >90`
  - `--level 50-100`
  - `--price 1000-5000`
  - `--order price+` or `price-`
- `/market buy <listing_id>` - Purchase
- `/market sell <pokemon_id> <price>` - List for sale
- `/market cancel <listing_id>` - Remove listing
- `/market listings` - Your active listings

**Economics:**
- 5% seller fee on successful sales
- Listings expire after 7 days
- Maximum 10 active listings per user

### 10. Shop & Items

**Commands:**
- `/shop` - View categories
- `/buy <item> [quantity]` - Purchase
- `/inventory` or `/bag` - View items
- `/use <item> [pokemon_id]` - Use item

**Item Categories:**
| Category | Items |
|----------|-------|
| Evolution | Fire Stone, Water Stone, Thunder Stone, etc. |
| Battle | Leftovers, Choice Band, Life Orb, Focus Sash |
| Utility | Incense, Rare Candy, XP Boost |
| Consumable | Potions, Revives (for future PvE) |

### 11. Shiny Hunting

**Command:** `/shinyhunt <pokemon_name>`

**Chain Bonus:**
| Chain | Shiny Odds |
|-------|------------|
| 0-50 | 1/4096 |
| 51-100 | 1/2048 |
| 101-200 | 1/1024 |
| 200+ | 1/512 |

- Catching target species increases chain
- Catching different species resets chain
- `/shinyhunt` - View current progress

### 12. Incense (Private Spawns)

- Purchase from shop
- Activates for 1 hour
- Spawns Pokemon in your DMs every 30 seconds
- Only you can catch these spawns
- Perfect for focused hunting

### 13. User Profile & Stats

**Commands:**
- `/profile [@user]` - View profile
- `/balance` or `/bal` - Check Telecoins
- `/daily` - Claim daily reward
- `/pokedex` - View completion progress
- `/leaderboard` - Top trainers

**Profile Shows:**
- Trainer name & balance
- Total Pokemon caught
- Unique species caught
- Shinies owned
- Battle record (W/L/Rating)
- Join date

### 14. Mega Evolution

- Requires Mega Stone (species-specific)
- `/mega` during battle to transform
- Boosted stats for battle duration
- Only one Mega per battle
- Reverts after battle ends

### 15. Group Administration

**Commands (Admin Only):**
- `/settings` - Group configuration panel
  - Enable/disable spawns
  - Set spawn channel
  - Adjust spawn rate (1-100 messages)
  - Enable/disable battles
  - Set redirect channel for commands
- `/spawn` - Force spawn (1 hour cooldown)

---

## Database Schema

### Core Tables

```sql
-- Users table
CREATE TABLE users (
    telegram_id BIGINT PRIMARY KEY,
    username VARCHAR(255),
    balance BIGINT DEFAULT 0,
    daily_streak INTEGER DEFAULT 0,
    last_daily TIMESTAMP,
    selected_pokemon_id UUID,
    shiny_hunt_target INTEGER,
    shiny_hunt_chain INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    settings JSONB DEFAULT '{}'
);

-- Pokemon (user-owned instances)
CREATE TABLE pokemon (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id BIGINT REFERENCES users(telegram_id),
    species_id INTEGER REFERENCES pokemon_species(national_dex),
    nickname VARCHAR(50),
    level INTEGER DEFAULT 1,
    experience BIGINT DEFAULT 0,
    iv_hp INTEGER CHECK (iv_hp BETWEEN 0 AND 31),
    iv_atk INTEGER CHECK (iv_atk BETWEEN 0 AND 31),
    iv_def INTEGER CHECK (iv_def BETWEEN 0 AND 31),
    iv_spa INTEGER CHECK (iv_spa BETWEEN 0 AND 31),
    iv_spd INTEGER CHECK (iv_spd BETWEEN 0 AND 31),
    iv_spe INTEGER CHECK (iv_spe BETWEEN 0 AND 31),
    ev_hp INTEGER DEFAULT 0,
    ev_atk INTEGER DEFAULT 0,
    ev_def INTEGER DEFAULT 0,
    ev_spa INTEGER DEFAULT 0,
    ev_spd INTEGER DEFAULT 0,
    ev_spe INTEGER DEFAULT 0,
    nature VARCHAR(20),
    ability VARCHAR(50),
    is_shiny BOOLEAN DEFAULT FALSE,
    is_favorite BOOLEAN DEFAULT FALSE,
    moves VARCHAR(50)[] DEFAULT '{}',
    held_item VARCHAR(50),
    friendship INTEGER DEFAULT 70,
    original_trainer_id BIGINT,
    caught_at TIMESTAMP DEFAULT NOW(),
    caught_in_group BIGINT
);

-- Pokemon Species (static data)
CREATE TABLE pokemon_species (
    national_dex INTEGER PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    type1 VARCHAR(20) NOT NULL,
    type2 VARCHAR(20),
    base_hp INTEGER,
    base_atk INTEGER,
    base_def INTEGER,
    base_spa INTEGER,
    base_spd INTEGER,
    base_spe INTEGER,
    abilities TEXT[],
    hidden_ability VARCHAR(50),
    catch_rate INTEGER,
    base_friendship INTEGER,
    base_experience INTEGER,
    growth_rate VARCHAR(20),
    gender_ratio FLOAT,
    egg_groups TEXT[],
    evolution_chain_id INTEGER,
    sprite_url TEXT,
    sprite_shiny_url TEXT,
    generation INTEGER,
    is_legendary BOOLEAN DEFAULT FALSE,
    is_mythical BOOLEAN DEFAULT FALSE,
    forms JSONB
);

-- Moves
CREATE TABLE moves (
    id INTEGER PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    type VARCHAR(20) NOT NULL,
    category VARCHAR(20) NOT NULL, -- physical, special, status
    power INTEGER,
    accuracy INTEGER,
    pp INTEGER,
    priority INTEGER DEFAULT 0,
    effect TEXT,
    effect_chance INTEGER,
    target VARCHAR(30),
    flags JSONB
);

-- Pokemon Learnsets
CREATE TABLE pokemon_learnsets (
    species_id INTEGER REFERENCES pokemon_species(national_dex),
    move_id INTEGER REFERENCES moves(id),
    learn_method VARCHAR(20), -- level-up, tm, egg, tutor
    level_learned INTEGER,
    PRIMARY KEY (species_id, move_id, learn_method)
);

-- Groups (Telegram groups)
CREATE TABLE groups (
    chat_id BIGINT PRIMARY KEY,
    title VARCHAR(255),
    spawn_enabled BOOLEAN DEFAULT TRUE,
    spawn_channel_id BIGINT,
    redirect_channel_id BIGINT,
    spawn_threshold INTEGER DEFAULT 50,
    message_count INTEGER DEFAULT 0,
    last_spawn_at TIMESTAMP,
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Active Spawns
CREATE TABLE active_spawns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chat_id BIGINT REFERENCES groups(chat_id),
    species_id INTEGER REFERENCES pokemon_species(national_dex),
    message_id BIGINT,
    is_shiny BOOLEAN DEFAULT FALSE,
    spawned_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP,
    caught_by BIGINT REFERENCES users(telegram_id),
    caught_at TIMESTAMP
);

-- Market Listings
CREATE TABLE market_listings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    seller_id BIGINT REFERENCES users(telegram_id),
    pokemon_id UUID REFERENCES pokemon(id),
    price BIGINT NOT NULL,
    listed_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP,
    sold_at TIMESTAMP,
    buyer_id BIGINT REFERENCES users(telegram_id)
);

-- Trade History
CREATE TABLE trades (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user1_id BIGINT REFERENCES users(telegram_id),
    user2_id BIGINT REFERENCES users(telegram_id),
    user1_pokemon UUID[],
    user2_pokemon UUID[],
    user1_coins BIGINT DEFAULT 0,
    user2_coins BIGINT DEFAULT 0,
    completed_at TIMESTAMP DEFAULT NOW()
);

-- Battle History
CREATE TABLE battles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    player1_id BIGINT REFERENCES users(telegram_id),
    player2_id BIGINT REFERENCES users(telegram_id),
    winner_id BIGINT REFERENCES users(telegram_id),
    player1_team UUID[],
    player2_team UUID[],
    battle_log JSONB,
    started_at TIMESTAMP DEFAULT NOW(),
    ended_at TIMESTAMP
);

-- User Inventory
CREATE TABLE inventory (
    user_id BIGINT REFERENCES users(telegram_id),
    item_id INTEGER,
    quantity INTEGER DEFAULT 1,
    PRIMARY KEY (user_id, item_id)
);

-- Pokedex (tracking seen/caught)
CREATE TABLE pokedex_entries (
    user_id BIGINT REFERENCES users(telegram_id),
    species_id INTEGER REFERENCES pokemon_species(national_dex),
    seen BOOLEAN DEFAULT FALSE,
    caught BOOLEAN DEFAULT FALSE,
    caught_shiny BOOLEAN DEFAULT FALSE,
    first_caught_at TIMESTAMP,
    PRIMARY KEY (user_id, species_id)
);
```

---

## Technical Specifications

### Dependencies

```toml
[project]
name = "telemon"
version = "0.1.0"
requires-python = ">=3.11"

dependencies = [
    "aiogram>=3.4.0",           # Telegram bot framework
    "sqlalchemy[asyncio]>=2.0", # Async ORM
    "asyncpg>=0.29.0",          # PostgreSQL async driver
    "alembic>=1.13.0",          # Database migrations
    "redis>=5.0.0",             # Caching & sessions
    "aiohttp>=3.9.0",           # HTTP client
    "pydantic>=2.5.0",          # Settings & validation
    "pydantic-settings>=2.1.0", # Environment config
    "python-dotenv>=1.0.0",     # .env loading
    "structlog>=24.1.0",        # Structured logging
    "pillow>=10.2.0",           # Image processing
    "rapidfuzz>=3.6.0",         # Fuzzy string matching
    "orjson>=3.9.0",            # Fast JSON
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "pytest-cov>=4.1.0",
    "ruff>=0.2.0",
    "mypy>=1.8.0",
]
```

### Configuration (.env)

```bash
# Bot
BOT_TOKEN=your_telegram_bot_token
BOT_USERNAME=telemon_bot

# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/telemon
REDIS_URL=redis://localhost:6379/0

# Spawning
SPAWN_MESSAGE_THRESHOLD=50
SPAWN_TIME_MIN_MINUTES=5
SPAWN_TIME_MAX_MINUTES=15
SPAWN_TIMEOUT_SECONDS=120

# Economy
DAILY_REWARD_BASE=100
DAILY_STREAK_BONUS=10
CATCH_REWARD_MIN=10
CATCH_REWARD_MAX=100
MARKET_FEE_PERCENT=5

# Battle
BATTLE_TIMEOUT_SECONDS=60

# Shiny
SHINY_BASE_RATE=4096
SHINY_CHAIN_DIVISORS=[4096, 2048, 1024, 512]

# Logging
LOG_LEVEL=INFO
```

---

## Development Phases

### Phase 1: Foundation (Week 1-2)
- [x] Project planning and architecture
- [ ] Initialize Python project with dependencies
- [ ] Set up aiogram 3.x bot scaffold
- [ ] Configure PostgreSQL + SQLAlchemy 2.0 (async)
- [ ] Set up Alembic migrations
- [ ] Configure Redis for caching
- [ ] Create configuration system
- [ ] Set up logging
- [ ] Docker Compose for local dev
- [ ] Download and import Pokemon data (species, moves, abilities)

### Phase 2: Core Gameplay (Week 3-4)
- [ ] Implement spawn engine (hybrid triggers)
- [ ] Create spawn messages with Pokemon images
- [ ] Build catching system with name validation
- [ ] Add hint system
- [ ] Implement Pokemon collection (list, info, select)
- [ ] Create pagination with inline keyboards
- [ ] Add filtering and sorting

### Phase 3: Progression (Week 5-6)
- [ ] Implement XP and leveling system
- [ ] Create evolution system (all types)
- [ ] Build move learning system
- [ ] Add learnset data
- [ ] Implement stat calculations (IVs, EVs, nature)

### Phase 4: Battle System (Week 7-9)
- [ ] Create damage calculator
- [ ] Implement type effectiveness
- [ ] Add status conditions
- [ ] Implement weather effects
- [ ] Add entry hazards
- [ ] Create ability system
- [ ] Implement held items in battle
- [ ] Build duel command and challenge system
- [ ] Create battle UI with inline keyboards
- [ ] Add battle rewards

### Phase 5: Economy & Trading (Week 10-11)
- [ ] Implement Telecoin transactions
- [ ] Create daily rewards with streaks
- [ ] Build trading system
- [ ] Create trade UI
- [ ] Implement marketplace
- [ ] Add shop and inventory
- [ ] Create item usage system

### Phase 6: Advanced Features (Week 12-14)
- [ ] Implement shiny hunting chains
- [ ] Add incense system
- [ ] Create user profiles
- [ ] Build Pokedex tracking
- [ ] Add leaderboards
- [ ] Implement Mega Evolution
- [ ] Create group admin settings

### Phase 7: Polish & Launch (Week 15-16)
- [ ] Create help system
- [ ] Build tutorial for new users
- [ ] Add Redis caching
- [ ] Optimize database queries
- [ ] Add rate limiting
- [ ] Write tests
- [ ] Create deployment configuration
- [ ] Documentation

---

## Data Import Requirements

| Data Type | Count | Source |
|-----------|-------|--------|
| Pokemon Species | 1008+ | PokeAPI |
| Moves | 900+ | PokeAPI |
| Abilities | 300+ | PokeAPI |
| Items | 500+ | PokeAPI |
| Natures | 25 | Hardcoded |
| Type Chart | 18x18 | Hardcoded |
| Evolution Chains | 500+ | PokeAPI |
| Learnsets | 50,000+ | PokeAPI |
| Sprites | 1008+ | PokeAPI CDN |

---

## Estimated Timeline

| Phase | Duration | Deliverables |
|-------|----------|--------------|
| Phase 1 | 2 weeks | Project setup, database, data import |
| Phase 2 | 2 weeks | Spawning, catching, collection |
| Phase 3 | 2 weeks | Leveling, evolution, moves |
| Phase 4 | 3 weeks | Full battle system |
| Phase 5 | 2 weeks | Trading, market, shop |
| Phase 6 | 3 weeks | Advanced features |
| Phase 7 | 2 weeks | Polish, testing, launch |
| **Total** | **16 weeks** | Complete bot |

---

## Commands Reference

### General
| Command | Description |
|---------|-------------|
| `/start` | Welcome & registration |
| `/help` | Command list |
| `/profile [@user]` | View profile |
| `/balance` | Check Telecoins |
| `/daily` | Claim daily reward |
| `/pokedex` | Pokedex progress |
| `/leaderboard` | Top trainers |

### Pokemon
| Command | Description |
|---------|-------------|
| `/catch <name>` | Catch Pokemon |
| `/c <name>` | Catch (short) |
| `/hint` | Get name hint |
| `/pokemon` | List your Pokemon |
| `/p` | List (short) |
| `/info [id]` | Pokemon details |
| `/select <id>` | Set active Pokemon |
| `/nickname <id> <name>` | Rename |
| `/release <id>` | Release Pokemon |
| `/favorite <id>` | Toggle favorite |

### Moves & Evolution
| Command | Description |
|---------|-------------|
| `/moves [id]` | View moves |
| `/learn <move>` | Learn move |
| `/forget <slot>` | Forget move |
| `/moveinfo <move>` | Move details |
| `/evolve <id>` | Evolve Pokemon |
| `/train` | Train active Pokemon |

### Battle
| Command | Description |
|---------|-------------|
| `/duel @user` | Challenge to battle |
| `/mega` | Mega evolve (in battle) |

### Trading
| Command | Description |
|---------|-------------|
| `/trade @user` | Start trade |
| `/trade add <id>` | Add Pokemon |
| `/trade add coins <n>` | Add Telecoins |
| `/trade remove <id>` | Remove Pokemon |
| `/trade confirm` | Confirm trade |
| `/trade cancel` | Cancel trade |

### Market
| Command | Description |
|---------|-------------|
| `/market search` | Browse market |
| `/market buy <id>` | Buy listing |
| `/market sell <id> <price>` | List for sale |
| `/market cancel <id>` | Remove listing |
| `/market listings` | Your listings |

### Shop
| Command | Description |
|---------|-------------|
| `/shop` | View shop |
| `/buy <item> [qty]` | Purchase item |
| `/inventory` | View items |
| `/bag` | View items (short) |
| `/use <item> [id]` | Use item |

### Hunting
| Command | Description |
|---------|-------------|
| `/shinyhunt <name>` | Set target |
| `/shinyhunt` | View progress |
| `/incense` | Use incense |

### Admin (Group)
| Command | Description |
|---------|-------------|
| `/settings` | Group settings |
| `/spawn` | Force spawn |

---

## Notes

- **Legal:** Using official Pokemon assets (sprites, names) is in a gray area. Consider using fan-made sprites or adding disclaimers.
- **Scaling:** For 100+ groups, consider horizontal scaling with multiple bot instances.
- **Monetization:** Telecoins are the in-game currency. Real-money monetization requires careful legal review.
- **Updates:** New Pokemon generations can be added by importing new PokeAPI data.

---

*Last Updated: February 2026*
*Project: Telemon*
