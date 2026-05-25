from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from config import ADMINS
from core.db import get_admins


class AdminMiddleware(BaseMiddleware):
    """Allow handler execution only if the event's user is an admin.

    Admins come from two sources:
      - ADMINS env var (permanent, super-admins)
      - the `admins` table (runtime, manageable via /admin)
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
