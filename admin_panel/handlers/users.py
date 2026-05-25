"""User management: find (with inline Ban/Unban on the result) + ban / unban via menu."""

import html

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from admin_panel import keyboards as kb
from admin_panel import texts as T
from admin_panel.db import (
    ban_user,
    get_admins,
    get_user_info,
    is_banned,
    log_action,
    unban_user,
)
from admin_panel.handlers.common import parse_id
from admin_panel.middleware import is_admin
from admin_panel.states import Admin
from config import ADMINS

router = Router(name="admin_users")


async def _user_info_text(tg_id: int) -> tuple[str, bool] | None:
    """Return (html_text, is_banned_flag) for the user, or None if not found."""
    info = await get_user_info(tg_id)
    if info is None:
        return None
    username = f"@{info['username']}" if info["username"] else "—"
    banned = await is_banned(tg_id)
    text = T.MSG_USER_INFO.format(
        id=info["telegram_id"],
        name=html.escape(info["name"] or ""),
        username=html.escape(username),
        joined=info["created_at"],
        is_admin="yes" if await is_admin(tg_id) else "no",
        is_banned="yes" if banned else "no",
    )
    return text, banned


# ---- users menu ----

@router.message(Admin.main, F.text == T.BTN_USERS)
async def open_users(message: Message, state: FSMContext) -> None:
    await state.set_state(Admin.users)
    await message.answer(T.TITLE_USERS, reply_markup=kb.users_menu(), parse_mode="HTML")


@router.message(Admin.users, F.text == T.BTN_BACK)
async def users_back(message: Message, state: FSMContext) -> None:
    await state.set_state(Admin.main)
    await message.answer(T.TITLE_MAIN, reply_markup=kb.main_menu(), parse_mode="HTML")


# ---- find user (with inline ban/unban on the result) ----

@router.message(Admin.users, F.text == T.BTN_USER_FIND)
async def user_find_prompt(message: Message, state: FSMContext) -> None:
    await state.set_state(Admin.user_find_input)
    await message.answer(
        "Send the Telegram ID to look up. You can keep sending IDs; "
        "press ❌ Cancel to return.",
        reply_markup=kb.cancel_kb(),
    )


@router.message(Admin.user_find_input, F.text == T.BTN_CANCEL)
async def user_find_cancel(message: Message, state: FSMContext) -> None:
    await state.set_state(Admin.users)
    await message.answer(T.TITLE_USERS, reply_markup=kb.users_menu(), parse_mode="HTML")


@router.message(Admin.user_find_input)
async def user_find_input(message: Message) -> None:
    tg_id = parse_id(message.text)
    if tg_id is None:
        await message.answer("❌ Invalid ID. Send a number.", reply_markup=kb.cancel_kb())
        return
    result = await _user_info_text(tg_id)
    if result is None:
        await message.answer(
            f"⚠️ User <code>{tg_id}</code> not found in the users table.",
            parse_mode="HTML",
        )
        return
    text, banned = result
    await message.answer(
        text,
        reply_markup=kb.user_actions_inline(tg_id, is_banned=banned),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("admin:user:ban:"))
async def user_ban_inline(call: CallbackQuery) -> None:
    tg_id = int(call.data.rsplit(":", 1)[1])
    if tg_id in ADMINS or tg_id in await get_admins():
        await call.answer("Can't ban an admin.", show_alert=True)
        return
    await ban_user(tg_id)
    await log_action(call.from_user.id, "ban_user", {"target": tg_id})
    result = await _user_info_text(tg_id)
    if result is not None:
        text, banned = result
        await call.message.edit_text(
            text,
            reply_markup=kb.user_actions_inline(tg_id, is_banned=banned),
            parse_mode="HTML",
        )
    await call.answer("🚫 Banned")


@router.callback_query(F.data.startswith("admin:user:unban:"))
async def user_unban_inline(call: CallbackQuery) -> None:
    tg_id = int(call.data.rsplit(":", 1)[1])
    if not await is_banned(tg_id):
        await call.answer("Not banned.", show_alert=True)
        return
    await unban_user(tg_id)
    await log_action(call.from_user.id, "unban_user", {"target": tg_id})
    result = await _user_info_text(tg_id)
    if result is not None:
        text, banned = result
        await call.message.edit_text(
            text,
            reply_markup=kb.user_actions_inline(tg_id, is_banned=banned),
            parse_mode="HTML",
        )
    await call.answer("✅ Unbanned")


# ---- ban (manual via menu) ----

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
    tg_id = parse_id(message.text)
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


# ---- unban (manual via menu) ----

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
    tg_id = parse_id(message.text)
    if tg_id is None:
        await message.answer("❌ Invalid ID.", reply_markup=kb.cancel_kb())
        return
    if not await is_banned(tg_id):
        await message.answer("⚠️ That user is not banned.", reply_markup=kb.users_menu())
    else:
        await unban_user(tg_id)
        await log_action(message.from_user.id, "unban_user", {"target": tg_id})
        await message.answer(
            f"✅ User <code>{tg_id}</code> unbanned.",
            reply_markup=kb.users_menu(),
            parse_mode="HTML",
        )
    await state.set_state(Admin.users)
