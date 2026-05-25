import datetime
from typing import Optional

import aiosqlite

from config import DB_PATH


async def init_db() -> None:
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
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS admins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id TEXT UNIQUE NOT NULL
            )
            """
        )
        await db.commit()


async def user_exists(telegram_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT 1 FROM users WHERE telegram_id = ?", (telegram_id,)
        ) as cursor:
            return await cursor.fetchone() is not None


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


async def count_users() -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM users") as cursor:
            row = await cursor.fetchone()
    return row[0] if row else 0


async def count_new_users_last_24_hours() -> int:
    past_24_hours = datetime.datetime.now() - datetime.timedelta(hours=24)
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM users WHERE created_at >= ?", (past_24_hours,)
        ) as cursor:
            row = await cursor.fetchone()
    return row[0] if row else 0


async def clear_db() -> None:
    """Delete all users. Admins and channels are preserved."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM users")
        await db.commit()


async def get_user_ids() -> list[int]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT telegram_id FROM users") as cursor:
            return [row[0] for row in await cursor.fetchall()]


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


async def count_admins() -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM admins") as cursor:
            row = await cursor.fetchone()
    return row[0] if row else 0


async def get_admins() -> list[int]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT telegram_id FROM admins") as cursor:
            return [row[0] for row in await cursor.fetchall()]


async def get_admin_details() -> list[tuple[int, Optional[str]]]:
    admin_ids = await get_admins()
    if not admin_ids:
        return []
    placeholders = ",".join("?" for _ in admin_ids)
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            f"SELECT telegram_id, name FROM users WHERE telegram_id IN ({placeholders})",
            admin_ids,
        ) as cursor:
            return list(await cursor.fetchall())


async def get_channel_ids() -> list[str]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT channel_id FROM channels") as cursor:
            return [row[0] for row in await cursor.fetchall()]


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


async def on_startup() -> None:
    await init_db()
