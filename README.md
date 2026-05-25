# Aiogram Bot Template

A clean, ready-to-fork starter for building Telegram bots with
[aiogram](https://docs.aiogram.dev/) v3. It ships with a working admin panel
(stats, broadcast, runtime admin management, required-channel gating) backed
by SQLite, so you can focus on the features that make your bot yours.

## Features

- **/start** flow with optional "must join channel" gating
- **/admin** panel with inline keyboards:
  - 📊 Stats (total users, new users in last 24h, uptime, admin count)
  - 📤 Broadcast any message type, with live progress and blocked/failed counters
  - ⚙️ Settings — add/remove runtime admins, add/remove required channels, clear users table
- Permanent super-admins via env, plus runtime admins stored in SQLite
- Async SQLite (`aiosqlite`) with auto-created schema
- Admin-only middleware
- Graceful shutdown, structured logging, configurable DB path

## Quick start

### Prerequisites
- Python 3.10+
- A Telegram bot token from [@BotFather](https://t.me/BotFather)
- Your Telegram numeric ID (get it from [@userinfobot](https://t.me/userinfobot))

### Steps

```bash
git clone https://github.com/nishonow/aiogram-bot-template.git
cd aiogram-bot-template

python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env
# edit .env and fill in BOT_TOKEN and ADMINS

python app.py
```

Open Telegram, send `/start` to your bot, then `/admin` to access the panel.

### Run with Docker

```bash
docker build -t aiogram-bot .
docker run --rm --env-file .env -v "$(pwd)/data:/app/data" \
  -e DB_PATH=/app/data/bot.db aiogram-bot
```

## Configuration

All configuration is read from environment variables (see `.env.example`):

| Variable    | Required | Description                                                                 |
|-------------|----------|-----------------------------------------------------------------------------|
| `BOT_TOKEN` | yes      | Token from @BotFather                                                       |
| `ADMINS`    | yes      | Comma-separated Telegram user IDs with permanent admin access               |
| `DB_PATH`   | no       | Path to the SQLite file. Defaults to `bot.db`                               |
| `LOG_LEVEL` | no       | `DEBUG`, `INFO`, `WARNING`, `ERROR`. Defaults to `INFO`                     |

`ADMINS` is comma-separated *without* brackets:

```
ADMINS=123456789,987654321
```

## Required-channel gating

In the admin panel, open **Settings → Add Channel** and send either
`@your_channel_username` or the numeric channel ID (e.g. `-1001234567890`).
The bot must be a member of the channel — otherwise it can't check
membership. Users will be prompted to join before they can use the bot.

## Project structure

```
aiogram-bot-template/
├── app.py                       # entrypoint
├── config.py                    # env var loading + validation
├── requirements.txt
├── Dockerfile
├── .env.example
├── core/
│   ├── db.py                    # aiosqlite data layer
│   └── keyboards.py             # all inline / reply keyboards
├── handlers/
│   ├── admin.py                 # /admin panel
│   └── start.py                 # /start + sample feature
├── middlewares/
│   └── admin_middleware.py      # admin-only gate for /admin router
└── utils/
    ├── consts.py
    └── helpers.py               # channel-membership helpers + sample data
```

## Extending the template

- **Add a feature handler:** create `handlers/your_feature.py` with a
  `router = Router()`, import it in `handlers/__init__.py`, then
  `dp.include_router(handlers.your_feature.router)` in `app.py`.
- **Add a keyboard:** put it in `core/keyboards.py`. Use the
  `admin:*` callback-data namespace if it's part of the admin panel.
- **Add a table:** extend `core/db.py` — schema is created on startup
  in `init_db()`.

## License

MIT — see [LICENSE](LICENSE).

## Feedback

Questions or feedback: [@nishonow](https://t.me/nishonow) on Telegram.
