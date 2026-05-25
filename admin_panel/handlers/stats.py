"""Statistics screen — inline Refresh + Close on the same message."""

import time

from aiogram import F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.types import CallbackQuery, Message

from admin_panel import keyboards as kb
from admin_panel import texts as T
from admin_panel.db import (
    count_admins,
    count_banned,
    count_new_users_24h,
    count_users,
    get_channel_ids,
    is_maintenance,
)
from admin_panel.states import Admin
from config import ADMINS
from utils.consts import BOT_START_TIME

router = Router(name="admin_stats")


def _format_uptime() -> str:
    seconds = int(time.time() - BOT_START_TIME)
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, secs = divmod(rem, 60)
    return f"{days}d {hours}h {minutes}m {secs}s"


async def _stats_text() -> str:
    return (
        f"{T.TITLE_STATS}\n\n"
        f"👤 Users: <b>{await count_users()}</b>\n"
        f"🆕 New (24h): <b>{await count_new_users_24h()}</b>\n"
        f"🚫 Banned: <b>{await count_banned()}</b>\n"
        f"👑 Admins: <b>{await count_admins() + len(ADMINS)}</b>\n"
        f"📢 Channels: <b>{len(await get_channel_ids())}</b>\n"
        f"🔧 Maintenance: <b>{'ON' if await is_maintenance() else 'OFF'}</b>\n"
        f"🕒 Uptime: <code>{_format_uptime()}</code>"
    )


@router.message(Admin.main, F.text == T.BTN_STATS)
async def open_stats(message: Message) -> None:
    await message.answer(
        await _stats_text(),
        reply_markup=kb.stats_inline(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "admin:stats:refresh")
async def refresh_stats(call: CallbackQuery) -> None:
    try:
        await call.message.edit_text(
            await _stats_text(),
            reply_markup=kb.stats_inline(),
            parse_mode="HTML",
        )
        await call.answer("Refreshed")
    except TelegramAPIError:
        # content identical → "message is not modified"
        await call.answer("Up to date")
