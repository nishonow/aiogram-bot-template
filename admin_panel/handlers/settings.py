"""Settings root menu + DB backup, clear users, action log."""

import datetime
import html
import json
from pathlib import Path

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import FSInputFile, Message

from admin_panel import keyboards as kb
from admin_panel import texts as T
from admin_panel.db import clear_users, get_recent_actions, log_action
from admin_panel.states import Admin
from config import DB_PATH

router = Router(name="admin_settings")


# ---- settings root ----

@router.message(Admin.main, F.text == T.BTN_SETTINGS)
async def open_settings(message: Message, state: FSMContext) -> None:
    await state.set_state(Admin.settings)
    await message.answer(T.TITLE_SETTINGS, reply_markup=kb.settings_menu(), parse_mode="HTML")


@router.message(Admin.settings, F.text == T.BTN_BACK)
async def settings_back(message: Message, state: FSMContext) -> None:
    await state.set_state(Admin.main)
    await message.answer(T.TITLE_MAIN, reply_markup=kb.main_menu(), parse_mode="HTML")


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


# ---- clear users (with confirm) ----

@router.message(Admin.settings, F.text == T.BTN_CLEAR_USERS)
async def clear_users_prompt(message: Message, state: FSMContext) -> None:
    await state.set_state(Admin.clear_users_confirm)
    await message.answer(
        "⚠️ <b>Clear the users table?</b>\n\n"
        "This deletes every user. Admins, channels, and bans are kept. "
        "Cannot be undone.",
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
async def open_action_log(message: Message) -> None:
    rows = await get_recent_actions(limit=30)
    if not rows:
        await message.answer("No actions logged yet.", reply_markup=kb.settings_menu())
        return
    lines = [T.TITLE_ACTION_LOG, ""]
    for admin_id, action, details, created in rows:
        detail_str = ""
        if details:
            try:
                pairs = json.loads(details)
                detail_str = " · " + ", ".join(f"{k}={v}" for k, v in pairs.items())
            except ValueError:
                pass
        lines.append(
            f"<code>{created}</code> · <code>{admin_id}</code> · "
            f"<b>{html.escape(action)}</b>{html.escape(detail_str)}"
        )
    await message.answer("\n".join(lines), reply_markup=kb.settings_menu(), parse_mode="HTML")
