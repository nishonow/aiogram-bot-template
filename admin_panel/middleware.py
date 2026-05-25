from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from admin_panel.db import get_admins
from config import ADMINS


class AdminMiddleware(BaseMiddleware):
    """Allow handler execution only if the event's user is an admin.

    Admins come from two sources:
      - ADMINS env var (permanent super-admins, cannot be removed at runtime)
      - the `admins` table (managed from inside the panel)
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        if user is None:
            return None
        if user.id in ADMINS:
            return await handler(event, data)
        if user.id in await get_admins():
            return await handler(event, data)
        return None


async def is_admin(user_id: int) -> bool:
    if user_id in ADMINS:
        return True
    return user_id in await get_admins()
