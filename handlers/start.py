"""Bot-specific user-facing handlers.

This is what you customize — `/start`, your features, etc.
The admin panel lives in `admin_panel/` and stays untouched.
"""

import random

from aiogram import Bot, F, Router, types
from aiogram.filters import CommandStart
from aiogram.utils.keyboard import ReplyKeyboardBuilder

from core.db import add_user, user_exists
from utils.helpers import FUN_FACTS, check_channel_membership, send_channel_join_button

router = Router(name="user")


def _start_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.button(text="🎲 Random Fact")
    return builder.as_markup(resize_keyboard=True)


@router.message(CommandStart())
async def start_command(message: types.Message, bot: Bot) -> None:
    user = message.from_user
    if not await user_exists(user.id):
        await add_user(user.id, user.full_name, user.username)

    if not await check_channel_membership(bot, user.id):
        await send_channel_join_button(message, bot)
        return

    await message.answer(
        "👋 Welcome! Tap the button below to get a random fact.",
        reply_markup=_start_keyboard(),
    )


@router.message(F.text == "🎲 Random Fact")
async def random_fact_handler(message: types.Message, bot: Bot) -> None:
    if not await check_channel_membership(bot, message.from_user.id):
        await send_channel_join_button(message, bot)
        return
    await message.answer(f"🧐 Did you know?\n\n{random.choice(FUN_FACTS)}")
