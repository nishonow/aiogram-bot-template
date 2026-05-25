from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from admin_panel.db import get_banned_ids


class BanMiddleware(BaseMiddleware):
    """Drop updates from banned users before any user-facing handler runs.

    Banned IDs are cached per call (one DB hit per event).
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        if user is not None and user.id in await get_banned_ids():
            return None
        return await handler(event, data)
