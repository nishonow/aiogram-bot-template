"""Shared helpers and the catch-all fallback for unmatched text in admin states."""

from typing import Optional

from aiogram import Router
from aiogram.filters import StateFilter
from aiogram.types import Message

from admin_panel.states import Admin

router = Router(name="admin_common")


def parse_id(text: Optional[str]) -> Optional[int]:
    if not text:
        return None
    try:
        return int(text.strip())
    except ValueError:
        return None


@router.message(StateFilter(Admin))
async def admin_fallback(message: Message) -> None:
    await message.answer("Please use the buttons to navigate.")
