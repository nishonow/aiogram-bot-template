"""Maintenance-mode toggle — inline button flips state and updates the same message."""

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from admin_panel import keyboards as kb
from admin_panel import texts as T
from admin_panel.db import is_maintenance, log_action, set_maintenance
from admin_panel.states import Admin

router = Router(name="admin_maintenance")


async def _maintenance_text() -> str:
    on = await is_maintenance()
    badge = "🔴 ON" if on else "🟢 OFF"
    return (
        f"{T.TITLE_MAINTENANCE}\n\nStatus: <b>{badge}</b>\n\n"
        "When ON, only admins can use the bot. "
        "Non-admin users get a polite 'try later' message."
    )


@router.message(Admin.settings, F.text == T.BTN_MAINTENANCE)
async def open_maintenance(message: Message) -> None:
    on = await is_maintenance()
    await message.answer(
        await _maintenance_text(),
        reply_markup=kb.maintenance_inline(on),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "admin:maint:toggle")
async def maintenance_toggle(call: CallbackQuery) -> None:
    new_state = not await is_maintenance()
    await set_maintenance(new_state)
    await log_action(call.from_user.id, "toggle_maintenance", {"enabled": new_state})
    await call.message.edit_text(
        await _maintenance_text(),
        reply_markup=kb.maintenance_inline(new_state),
        parse_mode="HTML",
    )
    await call.answer(f"Maintenance {'ON' if new_state else 'OFF'}")
