"""User management: find / ban / unban."""

import html

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

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


# ---- menu ----

@router.message(Admin.main, F.text == T.BTN_USERS)
async def open_users(message: Message, state: FSMContext) -> None:
    await state.set_state(Admin.users)
    await message.answer(T.TITLE_USERS, reply_markup=kb.users_menu(), parse_mode="HTML")


@router.message(Admin.users, F.text == T.BTN_BACK)
async def users_back(message: Message, state: FSMContext) -> None:
    await state.set_state(Admin.main)
    await message.answer(T.TITLE_MAIN, reply_markup=kb.main_menu(), parse_mode="HTML")


# ---- find ----

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
    tg_id = parse_id(message.text)
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


# ---- ban ----

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


# ---- unban ----

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
