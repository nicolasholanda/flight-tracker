# flight-tracker

A small Telegram bot that keeps an eye on flight prices for you. Tell it where you're going, when, and how much you're willing to pay. It checks Google Flights every hour and pings you when a fare hits your target.

It costs nothing to run: no airline APIs, no paid scraping services. Prices come from Google Flights through [fast-flights](https://github.com/AWeirdDev/flights), and the whole thing runs in a single Docker container on your own machine using Telegram long polling, so you don't need a public URL or open ports.

## Features

- **Guided search in Telegram**: one-way or round trip, origin, destination and dates, step by step. You type cities in plain text ("Fortaleza", "Rio", "GRU"). If a name is ambiguous, the bot shows a list to pick from, including an "all airports" option for cities like Rio or São Paulo.
- **Price alerts**: set a maximum price from any search result. You're notified the first time a fare is at or below it, and again only when it drops further. If the price goes back above your target, the next drop alerts you again.
- **Booking links**: every result and alert links to the same search on Google Flights, where you can pick a seller and buy.
- **Price history**: see the lowest price from each hourly check and the best price seen so far.
- **Private by default**: only the owner can use it out of the box. Anyone else who sends `/start` creates a single access request, and you approve or deny it with one tap. They can't ask twice. `/users` and `/revoke` manage access later.
- **Limits**: 5 active alerts per user, 10 searches per user per hour, and at most 30 routes per hourly check. Identical routes across alerts are searched once.
- **Self-monitoring**: if the price checks fail several times in a row (Google changed something, or you got rate limited), the owner gets one warning, and another message once things recover.

## Tech stack

- Python 3.13
- [python-telegram-bot](https://python-telegram-bot.org/) 22 with its job queue (APScheduler)
- [fast-flights](https://pypi.org/project/fast-flights/) 3.1 for Google Flights
- SQLite with plain SQL migrations
- pydantic-settings for configuration
- pytest and pytest-asyncio
- Docker Compose
- Airport data from [OurAirports](https://ourairports.com/data/) (public domain)

## Running it

1. Create a bot with [@BotFather](https://t.me/BotFather) and copy the token.
2. Find your own Telegram user ID, for example by messaging [@userinfobot](https://t.me/userinfobot).
3. Create your config:

   ```bash
   cp .env.example .env
   ```

   Fill in `TELEGRAM_TOKEN` and `OWNER_CHAT_ID`. The other values are optional and already have sensible defaults.

4. Start it:

   ```bash
   docker compose up -d --build
   ```

5. Open your bot in Telegram and send `/start`.

The database lives in the `flight-data` Docker volume, so alerts survive restarts and rebuilds. Logs: `docker compose logs -f`.

### Commands

| Command | What it does |
|---|---|
| `/start` | Main menu (or an access request, for new users) |
| `/buscar` | Start a flight search |
| `/alertas` | List your active alerts |
| `/cancelar` | Cancel the current search |
| `/users` | Owner only: list users and approve or revoke them |
| `/revoke <id>` | Owner only: remove a user's access |

### Configuration

| Variable | Default | |
|---|---|---|
| `CHECK_INTERVAL_MINUTES` | `60` | How often alerts are checked |
| `CHECK_JITTER_SECONDS` | `300` | Random delay added to each check |
| `MAX_ACTIVE_WATCHES_PER_USER` | `5` | |
| `MAX_SEARCHES_PER_USER_PER_HOUR` | `10` | |
| `MAX_ROUTES_PER_RUN` | `30` | Routes searched per check; the least recently checked go first |
| `REQUEST_DELAY_SECONDS` | `3` | Pause between Google Flights requests |
| `FAILURE_ALERT_THRESHOLD` | `3` | Consecutive failed checks before the owner is warned |
| `CURRENCY` / `LANGUAGE` | `BRL` / `pt-BR` | |
| `TIMEZONE` | `America/Fortaleza` | Used to decide when an alert's date has passed |

## Local development

```bash
python -m venv .venv
.venv/Scripts/activate        # or source .venv/bin/activate
pip install -e ".[dev]"
python -m flight_tracker
```

Tests:

```bash
pytest                         # unit + integration, no network
RUN_LIVE=1 pytest -m live      # also hit the real Google Flights
```

To refresh the airport list from OurAirports:

```bash
python scripts/build_airports.py
```

## A word of caution

fast-flights is an unofficial client that reverse-engineers Google Flights. It can break whenever Google changes things, and automated access may go against Google's terms. The bot keeps request volume low (one search per route per hour, with pauses in between), but treat it as a personal tool, not a service.
