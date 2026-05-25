"""Bot-specific helpers: required-channel gating and sample fact data."""

import logging
from typing import Optional

from aiogram import Bot
from aiogram.enums import ChatMemberStatus
from aiogram.exceptions import TelegramAPIError
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from admin_panel.db import get_channel_ids

logger = logging.getLogger(__name__)

_MEMBER_STATUSES = {
    ChatMemberStatus.MEMBER,
    ChatMemberStatus.ADMINISTRATOR,
    ChatMemberStatus.CREATOR,
}


async def check_channel_membership(bot: Bot, user_id: int) -> bool:
    required = await get_channel_ids()
    if not required:
        return True
    for channel_id in required:
        try:
            cm = await bot.get_chat_member(chat_id=channel_id, user_id=user_id)
        except TelegramAPIError:
            logger.exception("membership check failed for %s", channel_id)
            return False
        if cm.status not in _MEMBER_STATUSES:
            return False
    return True


async def _resolve_channel(bot: Bot, channel_id: str) -> Optional[tuple[str, str]]:
    try:
        chat = await bot.get_chat(channel_id)
    except TelegramAPIError:
        logger.exception("failed to fetch channel %s", channel_id)
        return None
    if not chat.username:
        return None
    return chat.title or "Join channel", chat.username


async def send_channel_join_button(message: Message, bot: Bot) -> bool:
    channel_ids = await get_channel_ids()
    if not channel_ids:
        return True
    rows = []
    for channel_id in channel_ids:
        resolved = await _resolve_channel(bot, channel_id)
        if not resolved:
            continue
        title, username = resolved
        rows.append([InlineKeyboardButton(text=title, url=f"https://t.me/{username}")])
    if not rows:
        return True
    await message.answer(
        "❗ Please join the channel(s) below first, then press /start to continue. 🚀",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
    )
    return False


FUN_FACTS = [
    "Honey never spoils — 3,000-year-old pots from Egyptian tombs are still edible.",
    "Octopuses have three hearts; two stop beating when they swim.",
    "Bananas are berries, but strawberries are not.",
    "The Eiffel Tower can grow more than 6 inches in summer due to thermal expansion.",
    "A group of flamingos is called a 'flamboyance'.",
    "Sloths can hold their breath longer than dolphins — up to 40 minutes.",
    "Sharks predate trees: they've been around for over 400 million years.",
    "Wombat poop is cube-shaped, which helps it stay put as a territory marker.",
    "A blue whale's heart is so big a human could swim through its arteries.",
    "There are more stars in the universe than grains of sand on Earth.",
    "A day on Venus is longer than a year on Venus.",
    "Pineapples take about two years to grow before they're harvested.",
    "Sea otters hold hands when they sleep to keep from drifting apart.",
    "The dot over a lowercase 'i' or 'j' is called a 'tittle'.",
    "The shortest war in history lasted 38 minutes (Britain vs Zanzibar, 1896).",
    "Cows have best friends and get stressed when separated from them.",
    "An ostrich's eye is bigger than its brain.",
    "The first oranges weren't orange — they were green.",
    "Butterflies can taste with their feet.",
    "A group of crows is called a 'murder'.",
]
