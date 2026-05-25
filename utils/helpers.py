import logging
from typing import Optional

from aiogram import Bot
from aiogram.enums import ChatMemberStatus
from aiogram.exceptions import TelegramAPIError
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from core.db import get_channel_ids

logger = logging.getLogger(__name__)

_MEMBER_STATUSES = {
    ChatMemberStatus.MEMBER,
    ChatMemberStatus.ADMINISTRATOR,
    ChatMemberStatus.CREATOR,
}


async def check_channel_membership(bot: Bot, user_id: int) -> bool:
    required_channels = await get_channel_ids()
    if not required_channels:
        return True

    for channel_id in required_channels:
        try:
            chat_member = await bot.get_chat_member(chat_id=channel_id, user_id=user_id)
        except TelegramAPIError:
            logger.exception("Failed to check membership for channel %s", channel_id)
            return False
        if chat_member.status not in _MEMBER_STATUSES:
            return False
    return True


async def get_channel_username(bot: Bot, channel_id) -> Optional[str]:
    try:
        chat = await bot.get_chat(channel_id)
    except TelegramAPIError:
        logger.exception("Failed to fetch channel %s", channel_id)
        return None
    return chat.username


async def get_channel_name(bot: Bot, channel_id) -> Optional[str]:
    try:
        chat = await bot.get_chat(channel_id)
    except TelegramAPIError:
        logger.exception("Failed to fetch channel %s", channel_id)
        return None
    return chat.title


async def send_channel_join_button(message: Message, bot: Bot) -> bool:
    channel_ids = await get_channel_ids()
    if not channel_ids:
        return True

    rows = []
    for channel_id in channel_ids:
        username = await get_channel_username(bot, channel_id)
        name = await get_channel_name(bot, channel_id) or "Join channel"
        if not username:
            continue
        rows.append(
            [InlineKeyboardButton(text=name, url=f"https://t.me/{username}")]
        )

    if not rows:
        return True

    markup = InlineKeyboardMarkup(inline_keyboard=rows)
    await message.answer(
        "❗ Please join the channel(s) below first, then press /start to continue. 🚀",
        reply_markup=markup,
    )
    return False


FUN_FACTS = [
    "Honey never spoils. Archaeologists have found pots of honey in ancient Egyptian tombs that are over 3,000 years old and still perfectly edible.",
    "Octopuses have three hearts, and two of them stop beating when they swim.",
    "Bananas are berries, but strawberries are not!",
    "The Eiffel Tower can grow more than 6 inches during summer due to thermal expansion.",
    "A group of flamingos is called a 'flamboyance'.",
    "Sloths can hold their breath longer than dolphins—up to 40 minutes!",
    "Sharks existed before trees—they've been around for over 400 million years.",
    "Wombat poop is cube-shaped, which helps it stay in place and mark their territory.",
    "The heart of a blue whale is so big that a human could swim through its arteries.",
    "There are more stars in the universe than grains of sand on Earth.",
    "The inventor of the Pringles can is buried in one—his ashes were placed inside a Pringles can.",
    "A day on Venus is longer than a year on Venus due to its slow rotation.",
    "Pineapples take about two years to grow before they're ready to harvest.",
    "Sea otters hold hands when they sleep to keep from drifting apart.",
    "The dot over the lowercase letters 'i' and 'j' is called a 'tittle'.",
    "The shortest war in history was between Britain and Zanzibar on August 27, 1896. Zanzibar surrendered after 38 minutes.",
    "Cows have best friends and get stressed when they are separated.",
    "An ostrich's eye is bigger than its brain.",
    "The first oranges weren't orange—they were green.",
    "Koalas have fingerprints that are so similar to humans' that they can confuse crime scene investigators.",
    "Butterflies can taste with their feet.",
    "There's a species of jellyfish that is biologically immortal. It can revert to its juvenile form indefinitely.",
    "A group of crows is called a 'murder'.",
    "A chef's hat traditionally has 100 pleats to represent the 100 ways to cook an egg.",
]
