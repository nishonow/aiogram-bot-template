# Aiogram Bot Template

A ready-to-fork starter for Telegram bots built with
[aiogram](https://docs.aiogram.dev/) v3. Comes with a **drop-in admin
panel** any bot can plug into — reply-keyboard navigation, broadcast
with live progress, user management, maintenance mode, action log,
DB backup, and more.

## Features

### Admin panel (`admin_panel/` — drop-in for any aiogram bot)
- 📊 **Stats** — total users, new in 24h, bans, admins, channels, uptime, maintenance status
- 📤 **Broadcast** any message type:
  - Live progress every 25 sends (sent / blocked / failed counters)
  - ✏️ *Edit* before sending
  - 🛑 *Stop* mid-flight
- 👥 **Users**:
  - 🔍 Find by Telegram ID (shows name, username, joined date, admin/ban status)
  - 🚫 Ban / ✅ Unban (banned users are silently dropped by middleware)
- ⚙️ **Settings**:
  - 👑 Add / remove runtime admins (super-admins from env can't be removed)
  - 📢 Add / remove required channels (with reachability check)
  - 🔧 Maintenance mode toggle (non-admins get a "try later" message)
  - 💾 Download DB backup as a file
  - 📜 Action log (last 30 admin actions)
  - 🗑 Clear users table

Hybrid UI: **reply keyboards** for menu navigation (stay at the bottom
of the chat); **inline buttons** for actions that update a specific
message — stats refresh, maintenance toggle, clear-users confirm,
broadcast preview / progress / stop, user ban/unban from find result.
Every menu has a ⬅️ Back or ❌ Cancel button; the main menu has a
🚪 Exit button. No slash commands.

### Bot side
- `/start` flow with optional "must join channel" gating
- Sample feature (random fact) — replace with whatever your bot does
- Banned-user and maintenance middlewares automatically apply to all
  user-facing routers

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
# edit .env, fill in BOT_TOKEN and ADMINS

python app.py
```

Open Telegram, send `/start`, then `/admin` to access the panel.

### Run with Docker

```bash
docker build -t aiogram-bot .
docker run --rm --env-file .env -v "$(pwd)/data:/app/data" \
  -e DB_PATH=/app/data/bot.db aiogram-bot
```

## Configuration

| Variable    | Required | Description                                                                 |
|-------------|----------|-----------------------------------------------------------------------------|
| `BOT_TOKEN` | yes      | Token from @BotFather                                                       |
| `ADMINS`    | yes      | Comma-separated Telegram IDs of **super-admins** (can't be removed at runtime) |
| `DB_PATH`   | no       | Path to SQLite file. Defaults to `bot.db`                                   |
| `LOG_LEVEL` | no       | `DEBUG` / `INFO` / `WARNING` / `ERROR`. Defaults to `INFO`                  |

`ADMINS` format: `ADMINS=123456789,987654321` (no brackets).

## Required-channel gating

In the admin panel: **Settings → Required channels → Add channel**.
Provide `@your_channel_username` or the numeric channel ID
(e.g. `-1001234567890`). The bot must be a member of the channel.
Users will be prompted to join before they can use the bot.

## Project structure

```
aiogram-bot-template/
├── app.py                        # entrypoint — wires routers and middlewares
├── config.py                     # env loading + validation
├── requirements.txt
├── Dockerfile
├── .env.example
│
├── admin_panel/                  # drop-in admin module (use as-is in any bot)
│   ├── __init__.py               # exports: admin_router, AdminMiddleware, init_admin_tables
│   ├── keyboards.py              # reply keyboards
│   ├── states.py                 # FSM states
│   ├── db.py                     # admins, banned, channels, settings, action_log tables
│   ├── middleware.py             # AdminMiddleware
│   ├── texts.py                  # button labels & strings (edit to rebrand / localize)
│   └── handlers/                 # one file per feature area
│       ├── __init__.py           # combines all sub-routers
│       ├── main_menu.py          # /admin entry, Exit
│       ├── stats.py
│       ├── broadcast.py
│       ├── users.py              # find / ban / unban
│       ├── settings.py           # settings root + backup + clear + log
│       ├── admins.py             # add / remove runtime admins
│       ├── channels.py           # add / remove required channels
│       ├── maintenance.py        # maintenance toggle
│       └── common.py             # shared helpers + fallback handler
│
├── core/
│   └── db.py                     # `users` table (the bot's own data layer)
│
├── handlers/
│   └── start.py                  # /start, sample features — customize freely
│
├── middlewares/
│   ├── ban_middleware.py         # drops events from banned users
│   └── maintenance_middleware.py # blocks non-admins when maintenance is ON
│
└── utils/
    ├── consts.py                 # BOT_START_TIME for uptime calc
    └── helpers.py                # channel-join gating + sample fact data
```

## Using the admin panel in your own bot

The panel is self-contained. To drop it into another aiogram project:

1. Copy the `admin_panel/` folder over.
2. Make sure your bot has a `users` table with columns
   `telegram_id INTEGER`, `name TEXT`, `username TEXT`, `created_at TIMESTAMP`,
   or adapt the queries in `admin_panel/db.py` to your schema.
3. Wire it in `app.py`:

   ```python
   from admin_panel import admin_router, AdminMiddleware, init_admin_tables

   admin_router.message.middleware(AdminMiddleware())
   dp.include_router(admin_router)
   await init_admin_tables()
   ```

4. (Optional) Apply the user-facing middlewares to your routers:

   ```python
   from middlewares.ban_middleware import BanMiddleware
   from middlewares.maintenance_middleware import MaintenanceMiddleware

   user_router.message.middleware(BanMiddleware())
   user_router.message.middleware(MaintenanceMiddleware())
   ```

5. Edit `admin_panel/texts.py` to rebrand button labels or translate the UI.

## Extending the template

- **New user-facing feature:** add `handlers/feature_x.py` with a
  `router = Router()`, import in `handlers/__init__.py`, then
  `dp.include_router(handlers.feature_x.router)` in `app.py`.
- **New admin feature:** extend `admin_panel/states.py` with a state,
  `admin_panel/keyboards.py` with the buttons, and add handlers in
  `admin_panel/handlers.py`. Or keep your custom admin handlers in a
  separate router and include both.
- **New DB table:** add `CREATE TABLE IF NOT EXISTS` in the relevant
  `init_*` function so the schema is created at startup.

## License

MIT — see [LICENSE](LICENSE).

## Feedback

Questions or feedback: [@nishonow](https://t.me/nishonow) on Telegram.
