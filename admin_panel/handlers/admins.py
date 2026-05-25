"""Add / remove runtime admins."""

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from admin_panel import keyboards as kb
from admin_panel import texts as T
from admin_panel.db import add_admin, get_admins, log_action, remove_admin
from admin_panel.handlers.common import parse_id
from admin_panel.states import Admin
from config import ADMINS

router = Router(name="admin_admins")


async def _admins_text() -> str:
    super_lines = [f"• <code>{a}</code> (super)" for a in ADMINS]
    runtime_lines = [f"• <code>{a}</code>" for a in await get_admins()]
    body = "\n".join(super_lines + runtime_lines) or "<i>None</i>"
    return f"{T.TITLE_ADMINS}\n\n{body}"


# ---- menu ----

@router.message(Admin.settings, F.text == T.BTN_ADMINS)
async def open_admins(message: Message, state: FSMContext) -> None:
    await state.set_state(Admin.admins_menu)
    await message.answer(await _admins_text(), reply_markup=kb.admins_menu(), parse_mode="HTML")


@router.message(Admin.admins_menu, F.text == T.BTN_BACK)
async def admins_back(message: Message, state: FSMContext) -> None:
    await state.set_state(Admin.settings)
    await message.answer(T.TITLE_SETTINGS, reply_markup=kb.settings_menu(), parse_mode="HTML")


# ---- add ----

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
    tg_id = parse_id(message.text)
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


# ---- remove ----

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
    tg_id = parse_id(message.text)
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
