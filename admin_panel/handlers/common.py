"""Shared helpers, generic Close-message callback, and admin-state fallback."""

import logging
from typing import Optional

from aiogram import F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import StateFilter
from aiogram.types import CallbackQuery, Message

from admin_panel.states import Admin

logger = logging.getLogger(__name__)
router = Router(name="admin_common")


def parse_id(text: Optional[str]) -> Optional[int]:
    if not text:
        return None
    try:
        return int(text.strip())
    except ValueError:
        return None


@router.callback_query(F.data == "admin:close")
async def close_inline_message(call: CallbackQuery) -> None:
    """Generic 'close this message' button. Deletes the message it's attached to."""
    try:
        await call.message.delete()
    except TelegramAPIError:
        logger.debug("close: could not delete message")
    await call.answer()


@router.message(StateFilter(Admin))
async def admin_fallback(message: Message) -> None:
    await message.answer("Please use the buttons to navigate.")
