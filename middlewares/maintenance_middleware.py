from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject

from admin_panel.db import is_maintenance
from admin_panel.middleware import is_admin
from admin_panel.texts import MSG_MAINTENANCE_ON


class MaintenanceMiddleware(BaseMiddleware):
    """When maintenance mode is on, non-admin events are short-circuited
    with a friendly message instead of running the user handler."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        if user is None:
            return await handler(event, data)
        if not await is_maintenance():
            return await handler(event, data)
        if await is_admin(user.id):
            return await handler(event, data)
        if isinstance(event, Message):
            await event.answer(MSG_MAINTENANCE_ON)
        return None
