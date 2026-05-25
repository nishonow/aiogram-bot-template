"""Data layer for the admin panel.

Owns the `admins`, `banned_users`, `channels`, `bot_settings`, and
`action_log` tables. The panel also reads from the `users` table
(see `core.db`).
"""

import datetime
import json
from typing import Optional

import aiosqlite

from config import DB_PATH


# ---------------- schema ----------------

async def init_admin_tables() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS admins (
                telegram_id INTEGER PRIMARY KEY
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS banned_users (
                telegram_id INTEGER PRIMARY KEY,
                banned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                reason TEXT
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS channels (
                channel_id TEXT PRIMARY KEY
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS bot_settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS action_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_id INTEGER NOT NULL,
                action TEXT NOT NULL,
                details TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        await db.commit()


# ---------------- admins ----------------

async def add_admin(telegram_id: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO admins (telegram_id) VALUES (?)",
            (telegram_id,),
        )
        await db.commit()


async def remove_admin(telegram_id: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM admins WHERE telegram_id = ?", (telegram_id,)
        )
        await db.commit()


async def get_admins() -> list[int]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT telegram_id FROM admins") as cur:
            return [row[0] for row in await cur.fetchall()]


async def count_admins() -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM admins") as cur:
            row = await cur.fetchone()
    return row[0] if row else 0


# ---------------- banned ----------------

async def ban_user(telegram_id: int, reason: Optional[str] = None) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO banned_users (telegram_id, reason) VALUES (?, ?)",
            (telegram_id, reason),
        )
        await db.commit()


async def unban_user(telegram_id: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM banned_users WHERE telegram_id = ?", (telegram_id,)
        )
        await db.commit()


async def is_banned(telegram_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT 1 FROM banned_users WHERE telegram_id = ?", (telegram_id,)
        ) as cur:
            return await cur.fetchone() is not None


async def get_banned_ids() -> set[int]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT telegram_id FROM banned_users") as cur:
            return {row[0] for row in await cur.fetchall()}


async def count_banned() -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM banned_users") as cur:
            row = await cur.fetchone()
    return row[0] if row else 0


# ---------------- channels ----------------

async def add_channel(channel_id: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO channels (channel_id) VALUES (?)",
            (channel_id,),
        )
        await db.commit()


async def remove_channel(channel_id: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM channels WHERE channel_id = ?", (channel_id,)
        )
        await db.commit()


async def get_channel_ids() -> list[str]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT channel_id FROM channels") as cur:
            return [row[0] for row in await cur.fetchall()]


# ---------------- settings (key/value) ----------------

async def set_setting(key: str, value: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO bot_settings (key, value) VALUES (?, ?)",
            (key, value),
        )
        await db.commit()


async def get_setting(key: str, default: Optional[str] = None) -> Optional[str]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT value FROM bot_settings WHERE key = ?", (key,)
        ) as cur:
            row = await cur.fetchone()
    return row[0] if row else default


async def is_maintenance() -> bool:
    return (await get_setting("maintenance", "0")) == "1"


async def set_maintenance(enabled: bool) -> None:
    await set_setting("maintenance", "1" if enabled else "0")


# ---------------- action log ----------------

async def log_action(admin_id: int, action: str, details: Optional[dict] = None) -> None:
    payload = json.dumps(details) if details else None
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO action_log (admin_id, action, details) VALUES (?, ?, ?)",
            (admin_id, action, payload),
        )
        await db.commit()


async def get_recent_actions(limit: int = 30) -> list[tuple[int, str, Optional[str], str]]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT admin_id, action, details, created_at "
            "FROM action_log ORDER BY id DESC LIMIT ?",
            (limit,),
        ) as cur:
            return list(await cur.fetchall())


# ---------------- user lookups (read-only on `users`) ----------------

async def get_user_info(telegram_id: int) -> Optional[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT telegram_id, name, username, created_at "
            "FROM users WHERE telegram_id = ?",
            (telegram_id,),
        ) as cur:
            row = await cur.fetchone()
    if not row:
        return None
    return {
        "telegram_id": row[0],
        "name": row[1],
        "username": row[2],
        "created_at": row[3],
    }


async def count_users() -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM users") as cur:
            row = await cur.fetchone()
    return row[0] if row else 0


async def count_new_users_24h() -> int:
    past = datetime.datetime.now() - datetime.timedelta(hours=24)
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM users WHERE created_at >= ?", (past,)
        ) as cur:
            row = await cur.fetchone()
    return row[0] if row else 0


async def get_user_ids() -> list[int]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT telegram_id FROM users") as cur:
            return [row[0] for row in await cur.fetchall()]


async def clear_users() -> None:
    """Delete every row in the users table. Admins/channels/banned untouched."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM users")
        await db.commit()
