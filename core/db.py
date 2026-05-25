"""Core data layer for the bot's `users` table.

Admin-panel tables (admins, banned, channels, settings, action_log) live
in `admin_panel/db.py`. Both modules share the same SQLite file via
`config.DB_PATH`.
"""

from typing import Optional

import aiosqlite

from config import DB_PATH


async def init_users_table() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                name TEXT NOT NULL,
                username TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        await db.commit()


async def user_exists(telegram_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT 1 FROM users WHERE telegram_id = ?", (telegram_id,)
        ) as cur:
            return await cur.fetchone() is not None


async def add_user(telegram_id: int, name: str, username: Optional[str]) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT OR IGNORE INTO users (telegram_id, name, username)
            VALUES (?, ?, ?)
            """,
            (telegram_id, name, username),
        )
        await db.commit()
