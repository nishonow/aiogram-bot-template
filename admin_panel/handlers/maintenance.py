"""Maintenance-mode toggle (with Yes/No confirm)."""

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from admin_panel import keyboards as kb
from admin_panel import texts as T
from admin_panel.db import is_maintenance, log_action, set_maintenance
from admin_panel.states import Admin

router = Router(name="admin_maintenance")


async def _maintenance_text() -> str:
    state = "🔴 ON" if await is_maintenance() else "🟢 OFF"
    return (
        f"{T.TITLE_MAINTENANCE}\n\nStatus: <b>{state}</b>\n\n"
        "When ON, only admins can use the bot. Press ✅ Yes to toggle."
    )


@router.message(Admin.settings, F.text == T.BTN_MAINTENANCE)
async def open_maintenance(message: Message, state: FSMContext) -> None:
    await state.set_state(Admin.maintenance_confirm)
    await message.answer(
        await _maintenance_text(),
        reply_markup=kb.confirm_kb(),
        parse_mode="HTML",
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
