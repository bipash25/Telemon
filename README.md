# Telemon

A Pokemon-style game bot for Telegram, inspired by Poketwo (Discord).

## Features

- **Wild Pokemon Spawns** - Pokemon spawn in group chats based on activity
- **Catching System** - Identify and catch Pokemon by name
- **Pokemon Collection** - Manage your caught Pokemon with filters and sorting
- **Trading** - Trade Pokemon and Telecoins with other trainers
- **PvP Battles** - Turn-based battles with full type effectiveness
- **Global Market** - Buy and sell Pokemon on the marketplace
- **Shop & Items** - Purchase evolution stones, battle items, and more
- **Shiny Hunting** - Build chains to improve shiny odds

## Tech Stack

- **Python 3.11+** with async/await
- **aiogram 3.x** - Telegram Bot framework
- **PostgreSQL** - Primary database
- **Redis** - Caching and FSM storage
- **SQLAlchemy 2.0** - Async ORM
- **Alembic** - Database migrations

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 14+
- Redis 7+
- A Telegram Bot Token from [@BotFather](https://t.me/BotFather)

### Installation

1. **Clone and setup environment**
   ```bash
   cd Pikamon
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -e .
   ```

2. **Start databases with Docker**
   ```bash
   docker-compose up -d
   ```

3. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env and add your BOT_TOKEN
   ```

4. **Run database migrations**
   ```bash
   alembic upgrade head
   ```

5. **Import Pokemon data**
   ```bash
   # Download data from PokeAPI (takes 15-30 minutes)
   python scripts/import_pokemon_data.py
   
   # Seed the database
   python scripts/seed_database.py
   ```

6. **Start the bot**
   ```bash
   python -m telemon.main
   ```

## Project Structure

```
telemon/
├── src/telemon/
│   ├── bot/              # Telegram bot (handlers, keyboards, middlewares)
│   ├── core/             # Business logic (spawning, battle, trading)
│   ├── database/         # SQLAlchemy models and repositories
│   └── utils/            # Shared utilities
├── data/                 # Static Pokemon data (JSON)
├── scripts/              # Data import and seeding scripts
├── alembic/              # Database migrations
└── tests/                # Test suite
```

## Commands

### General
- `/start` - Start the bot
- `/help` - Show commands
- `/profile` - View your profile
- `/balance` - Check Telecoins
- `/daily` - Claim daily reward

### Pokemon
- `/catch <name>` - Catch a Pokemon
- `/hint` - Get a name hint
- `/pokemon` - List your Pokemon
- `/info [id]` - View details
- `/select <id>` - Set active Pokemon

### Trading & Market
- `/trade @user` - Start a trade
- `/market search` - Browse market
- `/shop` - View shop

### Battle
- `/duel @user` - Challenge to battle

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Format code
ruff format src tests

# Type check
mypy src
```

## License

This project is for educational purposes. Pokemon is a trademark of Nintendo/Game Freak/The Pokemon Company.

## Contributing

Contributions are welcome! Please read the development plan in `DEVELOPMENT_PLAN.md`.
