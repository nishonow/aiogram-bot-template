import os
import sys

from dotenv import load_dotenv

load_dotenv()


def _require(name: str) -> str:
    value = os.getenv(name)
    if not value:
        sys.exit(
            f"Missing required environment variable: {name}. "
            f"Copy .env.example to .env and fill in the values."
        )
    return value


def _parse_admin_ids(raw: str) -> list[int]:
    ids: list[int] = []
    for chunk in raw.replace("[", "").replace("]", "").split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        try:
            ids.append(int(chunk))
        except ValueError:
            sys.exit(f"Invalid Telegram ID in ADMINS: {chunk!r}")
    return ids


BOT_TOKEN: str = _require("BOT_TOKEN")
ADMINS: list[int] = _parse_admin_ids(_require("ADMINS"))
DB_PATH: str = os.getenv("DB_PATH", "bot.db")
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()
