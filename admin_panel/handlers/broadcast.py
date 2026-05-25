"""Broadcast flow: collect → preview (inline) → send with inline progress + Stop."""

import asyncio
import logging

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError, TelegramForbiddenError
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from admin_panel import keyboards as kb
from admin_panel import texts as T
from admin_panel.db import get_user_ids, log_action
from admin_panel.states import Admin

logger = logging.getLogger(__name__)
router = Router(name="admin_broadcast")

BROADCAST_DELAY = 0.05  # ~20 msg/s, under Telegram's per-bot limit
PROGRESS_UPDATE_EVERY = 25

# admin_ids that have requested broadcast cancellation
_cancel_requests: set[int] = set()


# ---------------- input ----------------

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
    await state.update_data(
        source_chat_id=message.chat.id,
        source_message_id=message.message_id,
    )
    await state.set_state(Admin.broadcast_preview)
    await message.answer(
        T.TITLE_BROADCAST_PREVIEW,
        reply_markup=kb.broadcast_preview_inline(),
    )


# ---------------- preview (inline) ----------------

@router.callback_query(F.data == "admin:bc:edit", Admin.broadcast_preview)
async def broadcast_edit(call: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(Admin.broadcast_input)
    await call.message.edit_text(
        "✏️ Send a new broadcast message.",
        reply_markup=None,
    )
    await call.answer()


@router.callback_query(F.data == "admin:bc:cancel", Admin.broadcast_preview)
async def broadcast_cancel(call: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(Admin.main)
    await call.message.edit_text("🚫 Broadcast cancelled.", reply_markup=None)
    await call.message.answer(T.TITLE_MAIN, reply_markup=kb.main_menu(), parse_mode="HTML")
    await call.answer()


@router.callback_query(F.data == "admin:bc:send", Admin.broadcast_preview)
async def broadcast_send(call: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    data = await state.get_data()
    src_chat = data.get("source_chat_id")
    src_msg = data.get("source_message_id")
    await state.set_state(Admin.main)

    if not src_chat or not src_msg:
        await call.message.edit_text("⚠️ Source message lost. Try again.", reply_markup=None)
        await call.message.answer(T.TITLE_MAIN, reply_markup=kb.main_menu(), parse_mode="HTML")
        await call.answer()
        return

    user_ids = await get_user_ids()
    total = len(user_ids)
    if total == 0:
        await call.message.edit_text("ℹ️ No users to broadcast to.", reply_markup=None)
        await call.message.answer(T.TITLE_MAIN, reply_markup=kb.main_menu(), parse_mode="HTML")
        await call.answer()
        return

    admin_id = call.from_user.id
    _cancel_requests.discard(admin_id)

    # Switch the preview message into a live progress display with inline Stop.
    await call.message.edit_text(
        f"📤 Sending to {total} users…",
        reply_markup=kb.broadcast_stop_inline(),
    )
    await call.answer()

    sent = blocked = failed = 0
    cancelled = False

    for index, uid in enumerate(user_ids, start=1):
        if admin_id in _cancel_requests:
            cancelled = True
            _cancel_requests.discard(admin_id)
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
                await call.message.edit_text(
                    f"📤 Broadcasting…\n\n"
                    f"Progress: {index}/{total}\n"
                    f"✅ Sent: {sent}\n"
                    f"🚫 Blocked: {blocked}\n"
                    f"⚠️ Failed: {failed}",
                    reply_markup=kb.broadcast_stop_inline(),
                )
            except TelegramAPIError:
                pass
        await asyncio.sleep(BROADCAST_DELAY)

    status = "🛑 <b>Cancelled</b>" if cancelled else "✅ <b>Complete</b>"
    summary = (
        f"{status}\n\n"
        f"Recipients: <b>{total}</b>\n"
        f"✅ Sent: <b>{sent}</b>\n"
        f"🚫 Blocked: <b>{blocked}</b>\n"
        f"⚠️ Failed: <b>{failed}</b>"
    )
    try:
        await call.message.edit_text(summary, reply_markup=None, parse_mode="HTML")
    except TelegramAPIError:
        await call.message.answer(summary, parse_mode="HTML")

    await call.message.answer(T.TITLE_MAIN, reply_markup=kb.main_menu(), parse_mode="HTML")
    await log_action(
        admin_id,
        "broadcast",
        {"recipients": total, "sent": sent, "blocked": blocked,
         "failed": failed, "cancelled": cancelled},
    )


@router.callback_query(F.data == "admin:bc:stop")
async def broadcast_stop(call: CallbackQuery) -> None:
    _cancel_requests.add(call.from_user.id)
    await call.answer("Stopping after the current send…", show_alert=False)
