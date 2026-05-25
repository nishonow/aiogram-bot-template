"""All admin-panel handlers, driven by ReplyKeyboard buttons + FSM states.

The flow is: each "screen" is a state, each button is matched by exact
text within that state. Pressing `Back` / `Cancel` walks up the state tree.
"""

import asyncio
import csv
import datetime
import html
import io
import json
import logging
import time
from pathlib import Path
from typing import Optional

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError, TelegramForbiddenError
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, FSInputFile, Message

from admin_panel import keyboards as kb
from admin_panel import texts as T
from admin_panel.db import (
    add_admin,
    add_channel,
    ban_user,
    clear_users,
    count_admins,
    count_banned,
    count_new_users_24h,
    count_users,
    get_admins,
    get_channel_ids,
    get_recent_actions,
    get_user_ids,
    get_user_info,
    is_banned,
    is_maintenance,
    list_users,
    log_action,
    remove_admin,
    remove_channel,
    set_maintenance,
    unban_user,
)
from admin_panel.middleware import is_admin
from admin_panel.states import Admin
from config import ADMINS, DB_PATH
from utils.consts import BOT_START_TIME

logger = logging.getLogger(__name__)
router = Router(name="admin_panel")

USERS_PER_PAGE = 10
BROADCAST_DELAY = 0.05
PROGRESS_UPDATE_EVERY = 25

# admin_ids that have requested broadcast cancellation
_broadcast_cancel: set[int] = set()


# ============================================================
# helpers
# ============================================================

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


async def _admins_text() -> str:
    super_lines = [f"• <code>{a}</code> (super)" for a in ADMINS]
    runtime = await get_admins()
    runtime_lines = [f"• <code>{a}</code>" for a in runtime]
    body = "\n".join(super_lines + runtime_lines) or "<i>None</i>"
    return f"{T.TITLE_ADMINS}\n\n{body}"


async def _channels_text() -> str:
    channels = await get_channel_ids()
    body = "\n".join(f"• <code>{html.escape(c)}</code>" for c in channels) or "<i>None</i>"
    return f"{T.TITLE_CHANNELS}\n\n{body}"


async def _maintenance_text() -> str:
    state = "🔴 ON" if await is_maintenance() else "🟢 OFF"
    return (
        f"{T.TITLE_MAINTENANCE}\n\nStatus: <b>{state}</b>\n\n"
        "When ON, only admins can use the bot. Toggle below."
    )


async def _send_users_page(message: Message, state: FSMContext, page: int) -> None:
    total = await count_users()
    if total == 0:
        await message.answer("No users yet.", reply_markup=kb.users_menu())
        await state.set_state(Admin.users)
        return

    total_pages = max(1, (total + USERS_PER_PAGE - 1) // USERS_PER_PAGE)
    page = max(0, min(page, total_pages - 1))
    rows = await list_users(USERS_PER_PAGE, page * USERS_PER_PAGE)

    lines = [f"<b>Users</b> — page {page + 1}/{total_pages} ({total} total)\n"]
    for idx, (tg_id, name, username, created) in enumerate(rows, start=1 + page * USERS_PER_PAGE):
        name_safe = html.escape(name or "")
        un = f"@{html.escape(username)}" if username else "—"
        lines.append(f"{idx}. <code>{tg_id}</code> · {name_safe} · {un}")

    await state.update_data(users_page=page)
    await message.answer("\n".join(lines), reply_markup=kb.users_list_kb(), parse_mode="HTML")


def _parse_id(text: Optional[str]) -> Optional[int]:
    if not text:
        return None
    try:
        return int(text.strip())
    except ValueError:
        return None


# ============================================================
# entry, exit, /cancel
# ============================================================

@router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext) -> None:
    await state.set_state(Admin.main)
    await message.answer(T.TITLE_MAIN, reply_markup=kb.main_menu(), parse_mode="HTML")


@router.message(Command("cancel"), StateFilter(Admin))
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    await state.set_state(Admin.main)
    await message.answer(T.MSG_CANCELLED, reply_markup=kb.main_menu())


@router.message(Admin.main, F.text == T.BTN_EXIT)
@router.message(Command("exit"), StateFilter(Admin))
async def exit_panel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(T.MSG_EXIT, reply_markup=kb.remove_kb())


# ============================================================
# main menu navigation
# ============================================================

@router.message(Admin.main, F.text == T.BTN_STATS)
async def open_stats(message: Message, state: FSMContext) -> None:
    await state.set_state(Admin.stats)
    await message.answer(await _stats_text(), reply_markup=kb.stats_kb(), parse_mode="HTML")


@router.message(Admin.stats, F.text == T.BTN_REFRESH)
async def refresh_stats(message: Message) -> None:
    await message.answer(await _stats_text(), reply_markup=kb.stats_kb(), parse_mode="HTML")


@router.message(Admin.stats, F.text == T.BTN_BACK)
async def stats_back(message: Message, state: FSMContext) -> None:
    await state.set_state(Admin.main)
    await message.answer(T.TITLE_MAIN, reply_markup=kb.main_menu(), parse_mode="HTML")


# ============================================================
# broadcast
# ============================================================

@router.message(Admin.main, F.text == T.BTN_BROADCAST)
async def broadcast_start(message: Message, state: FSMContext) -> None:
    await state.set_state(Admin.broadcast_input)
    await message.answer(T.TITLE_BROADCAST_PROMPT, reply_markup=kb.cancel_kb())


@router.message(Admin.broadcast_input, F.text == T.BTN_CANCEL)
async def broadcast_input_cancel(message: Message, state: FSMContext) -> None:
    await state.set_state(Admin.main)
    await message.answer(T.MSG_CANCELLED, reply_markup=kb.main_menu())


@router.message(Admin.broadcast_input)
async def broadcast_input(message: Message, state: FSMContext) -> None:
    if message.text and message.text == T.BTN_CANCEL:
        return  # handled above
    await state.update_data(
        source_chat_id=message.chat.id,
        source_message_id=message.message_id,
    )
    await state.set_state(Admin.broadcast_preview)
    await message.answer(T.TITLE_BROADCAST_PREVIEW, reply_markup=kb.broadcast_preview_kb())


@router.message(Admin.broadcast_preview, F.text == T.BTN_BROADCAST_EDIT)
async def broadcast_edit(message: Message, state: FSMContext) -> None:
    await state.set_state(Admin.broadcast_input)
    await message.answer(T.TITLE_BROADCAST_PROMPT, reply_markup=kb.cancel_kb())


@router.message(Admin.broadcast_preview, F.text == T.BTN_CANCEL)
async def broadcast_preview_cancel(message: Message, state: FSMContext) -> None:
    await state.set_state(Admin.main)
    await message.answer(T.MSG_CANCELLED, reply_markup=kb.main_menu())


@router.message(Admin.broadcast_preview, F.text == T.BTN_BROADCAST_TEST)
async def broadcast_test(message: Message, state: FSMContext, bot: Bot) -> None:
    data = await state.get_data()
    src_chat = data.get("source_chat_id")
    src_msg = data.get("source_message_id")
    if not src_chat or not src_msg:
        await message.answer("⚠️ Source message lost. Try again.", reply_markup=kb.main_menu())
        await state.set_state(Admin.main)
        return
    try:
        await bot.copy_message(
            chat_id=message.from_user.id, from_chat_id=src_chat, message_id=src_msg
        )
        await message.answer("🧪 Test message sent.", reply_markup=kb.broadcast_preview_kb())
    except TelegramAPIError as exc:
        await message.answer(f"⚠️ Test failed: {exc}", reply_markup=kb.broadcast_preview_kb())


@router.message(Admin.broadcast_preview, F.text == T.BTN_BROADCAST_SEND)
async def broadcast_send(message: Message, state: FSMContext, bot: Bot) -> None:
    data = await state.get_data()
    src_chat = data.get("source_chat_id")
    src_msg = data.get("source_message_id")
    if not src_chat or not src_msg:
        await message.answer("⚠️ Source message lost. Try again.", reply_markup=kb.main_menu())
        await state.set_state(Admin.main)
        return

    user_ids = await get_user_ids()
    total = len(user_ids)
    if total == 0:
        await message.answer("ℹ️ No users to broadcast to.", reply_markup=kb.main_menu())
        await state.set_state(Admin.main)
        return

    admin_id = message.from_user.id
    _broadcast_cancel.discard(admin_id)
    await state.set_state(Admin.broadcast_sending)

    progress = await message.answer(
        f"📤 Sending to {total} users…\n\nPress <b>Stop</b> to cancel mid-flight.",
        reply_markup=kb.broadcast_running_kb(),
        parse_mode="HTML",
    )

    sent = blocked = failed = 0
    cancelled = False

    for index, uid in enumerate(user_ids, start=1):
        if admin_id in _broadcast_cancel:
            cancelled = True
            _broadcast_cancel.discard(admin_id)
            break
        try:
            await bot.copy_message(chat_id=uid, from_chat_id=src_chat, message_id=src_msg)
            sent += 1
        except TelegramForbiddenError:
            blocked += 1
        except TelegramAPIError as exc:
            failed += 1
            logger.warning("broadcast to %s failed: %s", uid, exc)

        if index % PROGRESS_UPDATE_EVERY == 0:
            try:
                await progress.edit_text(
                    f"📤 Broadcasting…\n\n"
                    f"Progress: {index}/{total}\n"
                    f"✅ Sent: {sent}\n"
                    f"🚫 Blocked: {blocked}\n"
                    f"⚠️ Failed: {failed}",
                )
            except TelegramAPIError:
                pass
        await asyncio.sleep(BROADCAST_DELAY)

    status = "🛑 Cancelled" if cancelled else "✅ Complete"
    summary = (
        f"{status}\n\n"
        f"Recipients: <b>{total}</b>\n"
        f"✅ Sent: <b>{sent}</b>\n"
        f"🚫 Blocked: <b>{blocked}</b>\n"
        f"⚠️ Failed: <b>{failed}</b>"
    )
    await message.answer(summary, reply_markup=kb.main_menu(), parse_mode="HTML")
    await log_action(
        admin_id,
        "broadcast",
        {"recipients": total, "sent": sent, "blocked": blocked, "failed": failed,
         "cancelled": cancelled},
    )
    await state.set_state(Admin.main)


@router.message(Admin.broadcast_sending, F.text == T.BTN_BROADCAST_STOP)
async def broadcast_stop(message: Message) -> None:
    _broadcast_cancel.add(message.from_user.id)
    await message.answer("🛑 Stopping after the current send…")


# ============================================================
# users
# ============================================================

@router.message(Admin.main, F.text == T.BTN_USERS)
async def open_users(message: Message, state: FSMContext) -> None:
    await state.set_state(Admin.users)
    await message.answer(T.TITLE_USERS, reply_markup=kb.users_menu(), parse_mode="HTML")


@router.message(Admin.users, F.text == T.BTN_BACK)
async def users_back(message: Message, state: FSMContext) -> None:
    await state.set_state(Admin.main)
    await message.answer(T.TITLE_MAIN, reply_markup=kb.main_menu(), parse_mode="HTML")


@router.message(Admin.users, F.text == T.BTN_USER_LIST)
async def users_list_start(message: Message, state: FSMContext) -> None:
    await state.set_state(Admin.users_list)
    await _send_users_page(message, state, page=0)


@router.message(Admin.users_list, F.text == T.BTN_PAGE_NEXT)
async def users_list_next(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    await _send_users_page(message, state, page=data.get("users_page", 0) + 1)


@router.message(Admin.users_list, F.text == T.BTN_PAGE_PREV)
async def users_list_prev(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    await _send_users_page(message, state, page=data.get("users_page", 0) - 1)


@router.message(Admin.users_list, F.text == T.BTN_BACK)
async def users_list_back(message: Message, state: FSMContext) -> None:
    await state.set_state(Admin.users)
    await message.answer(T.TITLE_USERS, reply_markup=kb.users_menu(), parse_mode="HTML")


@router.message(Admin.users, F.text == T.BTN_USER_FIND)
async def user_find_prompt(message: Message, state: FSMContext) -> None:
    await state.set_state(Admin.user_find_input)
    await message.answer("Send the Telegram ID to look up:", reply_markup=kb.cancel_kb())


@router.message(Admin.user_find_input, F.text == T.BTN_CANCEL)
async def user_find_cancel(message: Message, state: FSMContext) -> None:
    await state.set_state(Admin.users)
    await message.answer(T.TITLE_USERS, reply_markup=kb.users_menu(), parse_mode="HTML")


@router.message(Admin.user_find_input)
async def user_find_input(message: Message, state: FSMContext) -> None:
    tg_id = _parse_id(message.text)
    if tg_id is None:
        await message.answer("❌ Invalid ID. Send a number.", reply_markup=kb.cancel_kb())
        return
    info = await get_user_info(tg_id)
    if info is None:
        await message.answer(
            f"⚠️ User <code>{tg_id}</code> not found in the users table.",
            reply_markup=kb.users_menu(),
            parse_mode="HTML",
        )
    else:
        username = f"@{info['username']}" if info["username"] else "—"
        await message.answer(
            T.MSG_USER_INFO.format(
                id=info["telegram_id"],
                name=html.escape(info["name"] or ""),
                username=html.escape(username),
                joined=info["created_at"],
                is_admin="yes" if await is_admin(tg_id) else "no",
                is_banned="yes" if await is_banned(tg_id) else "no",
            ),
            reply_markup=kb.users_menu(),
            parse_mode="HTML",
        )
    await state.set_state(Admin.users)


@router.message(Admin.users, F.text == T.BTN_USER_BAN)
async def user_ban_prompt(message: Message, state: FSMContext) -> None:
    await state.set_state(Admin.user_ban_input)
    await message.answer("Send the Telegram ID to ban:", reply_markup=kb.cancel_kb())


@router.message(Admin.user_ban_input, F.text == T.BTN_CANCEL)
async def user_ban_cancel(message: Message, state: FSMContext) -> None:
    await state.set_state(Admin.users)
    await message.answer(T.TITLE_USERS, reply_markup=kb.users_menu(), parse_mode="HTML")


@router.message(Admin.user_ban_input)
async def user_ban_input(message: Message, state: FSMContext) -> None:
    tg_id = _parse_id(message.text)
    if tg_id is None:
        await message.answer("❌ Invalid ID.", reply_markup=kb.cancel_kb())
        return
    if tg_id in ADMINS or tg_id in await get_admins():
        await message.answer(
            "⚠️ Can't ban an admin. Remove admin rights first.",
            reply_markup=kb.users_menu(),
        )
        await state.set_state(Admin.users)
        return
    await ban_user(tg_id)
    await log_action(message.from_user.id, "ban_user", {"target": tg_id})
    await message.answer(
        f"🚫 User <code>{tg_id}</code> banned.",
        reply_markup=kb.users_menu(),
        parse_mode="HTML",
    )
    await state.set_state(Admin.users)


@router.message(Admin.users, F.text == T.BTN_USER_UNBAN)
async def user_unban_prompt(message: Message, state: FSMContext) -> None:
    await state.set_state(Admin.user_unban_input)
    await message.answer("Send the Telegram ID to unban:", reply_markup=kb.cancel_kb())


@router.message(Admin.user_unban_input, F.text == T.BTN_CANCEL)
async def user_unban_cancel(message: Message, state: FSMContext) -> None:
    await state.set_state(Admin.users)
    await message.answer(T.TITLE_USERS, reply_markup=kb.users_menu(), parse_mode="HTML")


@router.message(Admin.user_unban_input)
async def user_unban_input(message: Message, state: FSMContext) -> None:
    tg_id = _parse_id(message.text)
    if tg_id is None:
        await message.answer("❌ Invalid ID.", reply_markup=kb.cancel_kb())
        return
    if not await is_banned(tg_id):
        await message.answer(
            "⚠️ That user is not banned.",
            reply_markup=kb.users_menu(),
        )
    else:
        await unban_user(tg_id)
        await log_action(message.from_user.id, "unban_user", {"target": tg_id})
        await message.answer(
            f"✅ User <code>{tg_id}</code> unbanned.",
            reply_markup=kb.users_menu(),
            parse_mode="HTML",
        )
    await state.set_state(Admin.users)


@router.message(Admin.users, F.text == T.BTN_USER_EXPORT)
async def user_export(message: Message, bot: Bot) -> None:
    rows = await list_users(limit=10_000_000, offset=0)
    if not rows:
        await message.answer("No users to export.", reply_markup=kb.users_menu())
        return
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["telegram_id", "name", "username", "created_at"])
    writer.writerows(rows)
    data = buffer.getvalue().encode("utf-8")
    filename = f"users-{datetime.date.today().isoformat()}.csv"
    await bot.send_document(
        chat_id=message.chat.id,
        document=BufferedInputFile(data, filename=filename),
        caption=f"📥 {len(rows)} users exported.",
    )
    await log_action(message.from_user.id, "export_users", {"count": len(rows)})


# ============================================================
# settings: root menu
# ============================================================

@router.message(Admin.main, F.text == T.BTN_SETTINGS)
async def open_settings(message: Message, state: FSMContext) -> None:
    await state.set_state(Admin.settings)
    await message.answer(T.TITLE_SETTINGS, reply_markup=kb.settings_menu(), parse_mode="HTML")


@router.message(Admin.settings, F.text == T.BTN_BACK)
async def settings_back(message: Message, state: FSMContext) -> None:
    await state.set_state(Admin.main)
    await message.answer(T.TITLE_MAIN, reply_markup=kb.main_menu(), parse_mode="HTML")


# ---- admins submenu ----

@router.message(Admin.settings, F.text == T.BTN_ADMINS)
async def open_admins(message: Message, state: FSMContext) -> None:
    await state.set_state(Admin.admins_menu)
    await message.answer(await _admins_text(), reply_markup=kb.admins_menu(), parse_mode="HTML")


@router.message(Admin.admins_menu, F.text == T.BTN_BACK)
async def admins_back(message: Message, state: FSMContext) -> None:
    await state.set_state(Admin.settings)
    await message.answer(T.TITLE_SETTINGS, reply_markup=kb.settings_menu(), parse_mode="HTML")


@router.message(Admin.admins_menu, F.text == T.BTN_ADD_ADMIN)
async def admin_add_prompt(message: Message, state: FSMContext) -> None:
    await state.set_state(Admin.admin_add_input)
    await message.answer("Send the Telegram ID of the new admin:", reply_markup=kb.cancel_kb())


@router.message(Admin.admin_add_input, F.text == T.BTN_CANCEL)
async def admin_add_cancel(message: Message, state: FSMContext) -> None:
    await state.set_state(Admin.admins_menu)
    await message.answer(await _admins_text(), reply_markup=kb.admins_menu(), parse_mode="HTML")


@router.message(Admin.admin_add_input)
async def admin_add_input(message: Message, state: FSMContext) -> None:
    tg_id = _parse_id(message.text)
    if tg_id is None:
        await message.answer("❌ Invalid ID.", reply_markup=kb.cancel_kb())
        return
    if tg_id in ADMINS:
        await message.answer("⚠️ Already a super-admin.", reply_markup=kb.admins_menu())
    elif tg_id in await get_admins():
        await message.answer("⚠️ Already an admin.", reply_markup=kb.admins_menu())
    else:
        await add_admin(tg_id)
        await log_action(message.from_user.id, "add_admin", {"target": tg_id})
        await message.answer(
            f"✅ Added admin <code>{tg_id}</code>.",
            reply_markup=kb.admins_menu(),
            parse_mode="HTML",
        )
    await state.set_state(Admin.admins_menu)


@router.message(Admin.admins_menu, F.text == T.BTN_REMOVE_ADMIN)
async def admin_remove_prompt(message: Message, state: FSMContext) -> None:
    await state.set_state(Admin.admin_remove_input)
    await message.answer(
        "Send the Telegram ID of the admin to remove.\n"
        "<i>Super-admins (set via ADMINS env) can't be removed here.</i>",
        reply_markup=kb.cancel_kb(),
        parse_mode="HTML",
    )


@router.message(Admin.admin_remove_input, F.text == T.BTN_CANCEL)
async def admin_remove_cancel(message: Message, state: FSMContext) -> None:
    await state.set_state(Admin.admins_menu)
    await message.answer(await _admins_text(), reply_markup=kb.admins_menu(), parse_mode="HTML")


@router.message(Admin.admin_remove_input)
async def admin_remove_input(message: Message, state: FSMContext) -> None:
    tg_id = _parse_id(message.text)
    if tg_id is None:
        await message.answer("❌ Invalid ID.", reply_markup=kb.cancel_kb())
        return
    if tg_id in ADMINS:
        await message.answer(
            "⚠️ Super-admins can't be removed at runtime.",
            reply_markup=kb.admins_menu(),
        )
    elif tg_id not in await get_admins():
        await message.answer("⚠️ Not an admin.", reply_markup=kb.admins_menu())
    else:
        await remove_admin(tg_id)
        await log_action(message.from_user.id, "remove_admin", {"target": tg_id})
        await message.answer(
            f"✅ Removed admin <code>{tg_id}</code>.",
            reply_markup=kb.admins_menu(),
            parse_mode="HTML",
        )
    await state.set_state(Admin.admins_menu)


# ---- channels submenu ----

@router.message(Admin.settings, F.text == T.BTN_CHANNELS)
async def open_channels(message: Message, state: FSMContext) -> None:
    await state.set_state(Admin.channels_menu)
    await message.answer(
        await _channels_text(), reply_markup=kb.channels_menu(), parse_mode="HTML"
    )


@router.message(Admin.channels_menu, F.text == T.BTN_BACK)
async def channels_back(message: Message, state: FSMContext) -> None:
    await state.set_state(Admin.settings)
    await message.answer(T.TITLE_SETTINGS, reply_markup=kb.settings_menu(), parse_mode="HTML")


@router.message(Admin.channels_menu, F.text == T.BTN_ADD_CHANNEL)
async def channel_add_prompt(message: Message, state: FSMContext) -> None:
    await state.set_state(Admin.channel_add_input)
    await message.answer(
        "Send the channel to add. Use @username or numeric ID (e.g. <code>-1001234567890</code>).\n"
        "<i>The bot must be a member of the channel.</i>",
        reply_markup=kb.cancel_kb(),
        parse_mode="HTML",
    )


@router.message(Admin.channel_add_input, F.text == T.BTN_CANCEL)
async def channel_add_cancel(message: Message, state: FSMContext) -> None:
    await state.set_state(Admin.channels_menu)
    await message.answer(
        await _channels_text(), reply_markup=kb.channels_menu(), parse_mode="HTML"
    )


@router.message(Admin.channel_add_input)
async def channel_add_input(message: Message, state: FSMContext, bot: Bot) -> None:
    target = (message.text or "").strip()
    if not target:
        await message.answer("❌ Empty input.", reply_markup=kb.cancel_kb())
        return
    if target in await get_channel_ids():
        await message.answer("⚠️ Already in the list.", reply_markup=kb.channels_menu())
        await state.set_state(Admin.channels_menu)
        return
    try:
        chat = await bot.get_chat(target)
    except TelegramAPIError:
        await message.answer(
            "❌ Bot can't access that channel. Add the bot to it and try again.",
            reply_markup=kb.channels_menu(),
        )
        await state.set_state(Admin.channels_menu)
        return
    await add_channel(target)
    await log_action(message.from_user.id, "add_channel", {"target": target})
    await message.answer(
        f"✅ Channel <b>{html.escape(chat.title or target)}</b> added.",
        reply_markup=kb.channels_menu(),
        parse_mode="HTML",
    )
    await state.set_state(Admin.channels_menu)


@router.message(Admin.channels_menu, F.text == T.BTN_REMOVE_CHANNEL)
async def channel_remove_prompt(message: Message, state: FSMContext) -> None:
    await state.set_state(Admin.channel_remove_input)
    await message.answer(
        "Send the channel username or ID to remove:",
        reply_markup=kb.cancel_kb(),
    )


@router.message(Admin.channel_remove_input, F.text == T.BTN_CANCEL)
async def channel_remove_cancel(message: Message, state: FSMContext) -> None:
    await state.set_state(Admin.channels_menu)
    await message.answer(
        await _channels_text(), reply_markup=kb.channels_menu(), parse_mode="HTML"
    )


@router.message(Admin.channel_remove_input)
async def channel_remove_input(message: Message, state: FSMContext) -> None:
    target = (message.text or "").strip()
    if target not in await get_channel_ids():
        await message.answer("⚠️ Not in the list.", reply_markup=kb.channels_menu())
    else:
        await remove_channel(target)
        await log_action(message.from_user.id, "remove_channel", {"target": target})
        await message.answer(
            f"✅ Removed <code>{html.escape(target)}</code>.",
            reply_markup=kb.channels_menu(),
            parse_mode="HTML",
        )
    await state.set_state(Admin.channels_menu)


# ---- maintenance submenu ----

@router.message(Admin.settings, F.text == T.BTN_MAINTENANCE)
async def open_maintenance(message: Message, state: FSMContext) -> None:
    await state.set_state(Admin.maintenance_confirm)
    await message.answer(
        await _maintenance_text(),
        reply_markup=kb.confirm_kb(),
        parse_mode="HTML",
    )
    await message.answer(
        "Press ✅ Yes to toggle, ❌ No to go back.",
        reply_markup=kb.confirm_kb(),
    )


@router.message(Admin.maintenance_confirm, F.text == T.BTN_CONFIRM_YES)
async def maintenance_toggle(message: Message, state: FSMContext) -> None:
    new_state = not await is_maintenance()
    await set_maintenance(new_state)
    await log_action(message.from_user.id, "toggle_maintenance", {"enabled": new_state})
    await state.set_state(Admin.settings)
    await message.answer(
        f"🔧 Maintenance is now <b>{'ON' if new_state else 'OFF'}</b>.",
        reply_markup=kb.settings_menu(),
        parse_mode="HTML",
    )


@router.message(Admin.maintenance_confirm, F.text == T.BTN_CONFIRM_NO)
async def maintenance_cancel(message: Message, state: FSMContext) -> None:
    await state.set_state(Admin.settings)
    await message.answer(T.TITLE_SETTINGS, reply_markup=kb.settings_menu(), parse_mode="HTML")


# ---- DB backup ----

@router.message(Admin.settings, F.text == T.BTN_BACKUP)
async def backup_db(message: Message, bot: Bot) -> None:
    path = Path(DB_PATH)
    if not path.exists():
        await message.answer("⚠️ Database file not found.", reply_markup=kb.settings_menu())
        return
    await bot.send_document(
        chat_id=message.chat.id,
        document=FSInputFile(path),
        caption=f"💾 DB backup — {datetime.datetime.now().isoformat(timespec='seconds')}",
    )
    await log_action(message.from_user.id, "db_backup")


# ---- clear users ----

@router.message(Admin.settings, F.text == T.BTN_CLEAR_USERS)
async def clear_users_prompt(message: Message, state: FSMContext) -> None:
    await state.set_state(Admin.clear_users_confirm)
    await message.answer(
        "⚠️ <b>Clear the users table?</b>\n\n"
        "This deletes every user. Admins, channels, and bans are kept. Cannot be undone.",
        reply_markup=kb.confirm_kb(),
        parse_mode="HTML",
    )


@router.message(Admin.clear_users_confirm, F.text == T.BTN_CONFIRM_YES)
async def clear_users_confirm(message: Message, state: FSMContext) -> None:
    await clear_users()
    await log_action(message.from_user.id, "clear_users")
    await state.set_state(Admin.settings)
    await message.answer("🗑 Users table cleared.", reply_markup=kb.settings_menu())


@router.message(Admin.clear_users_confirm, F.text == T.BTN_CONFIRM_NO)
async def clear_users_cancel(message: Message, state: FSMContext) -> None:
    await state.set_state(Admin.settings)
    await message.answer(T.MSG_CANCELLED, reply_markup=kb.settings_menu())


# ---- action log ----

@router.message(Admin.settings, F.text == T.BTN_ACTION_LOG)
async def open_action_log(message: Message, state: FSMContext) -> None:
    rows = await get_recent_actions(limit=30)
    if not rows:
        await message.answer("No actions logged yet.", reply_markup=kb.settings_menu())
        return
    lines = [T.TITLE_ACTION_LOG, ""]
    for admin_id, action, details, created in rows:
        detail_str = ""
        if details:
            try:
                detail_str = " · " + ", ".join(f"{k}={v}" for k, v in json.loads(details).items())
            except ValueError:
                pass
        lines.append(
            f"<code>{created}</code> · <code>{admin_id}</code> · "
            f"<b>{html.escape(action)}</b>{html.escape(detail_str)}"
        )
    await message.answer("\n".join(lines), reply_markup=kb.settings_menu(), parse_mode="HTML")


# ============================================================
# fallback inside admin states (catches stray text)
# ============================================================

@router.message(StateFilter(Admin))
async def admin_fallback(message: Message) -> None:
    await message.answer("Please use the buttons. /cancel returns to the menu, /exit closes.")
