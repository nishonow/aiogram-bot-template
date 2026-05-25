"""Broadcast flow: collect message → preview → send with live progress + stop button."""

import asyncio
import logging

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError, TelegramForbiddenError
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from admin_panel import keyboards as kb
from admin_panel import texts as T
from admin_panel.db import get_user_ids, log_action
from admin_panel.states import Admin

logger = logging.getLogger(__name__)
router = Router(name="admin_broadcast")

BROADCAST_DELAY = 0.05  # ~20 msg/s, safely under Telegram's limit
PROGRESS_UPDATE_EVERY = 25

# admin_ids that requested broadcast cancellation
_cancel_requests: set[int] = set()


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
    await message.answer(T.TITLE_BROADCAST_PREVIEW, reply_markup=kb.broadcast_preview_kb())


@router.message(Admin.broadcast_preview, F.text == T.BTN_BROADCAST_EDIT)
async def broadcast_edit(message: Message, state: FSMContext) -> None:
    await state.set_state(Admin.broadcast_input)
    await message.answer(T.TITLE_BROADCAST_PROMPT, reply_markup=kb.cancel_kb())


@router.message(Admin.broadcast_preview, F.text == T.BTN_CANCEL)
async def broadcast_preview_cancel(message: Message, state: FSMContext) -> None:
    await state.set_state(Admin.main)
    await message.answer(T.MSG_CANCELLED, reply_markup=kb.main_menu())


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
    _cancel_requests.discard(admin_id)
    await state.set_state(Admin.broadcast_sending)

    progress = await message.answer(
        f"📤 Sending to {total} users…\n\nPress <b>Stop</b> to cancel mid-flight.",
        reply_markup=kb.broadcast_running_kb(),
        parse_mode="HTML",
    )

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
                await progress.edit_text(
                    f"📤 Broadcasting…\n\n"
                    f"Progress: {index}/{total}\n"
                    f"✅ Sent: {sent}\n"
                    f"🚫 Blocked: {blocked}\n"
                    f"⚠️ Failed: {failed}"
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
        {"recipients": total, "sent": sent, "blocked": blocked,
         "failed": failed, "cancelled": cancelled},
    )
    await state.set_state(Admin.main)


@router.message(Admin.broadcast_sending, F.text == T.BTN_BROADCAST_STOP)
async def broadcast_stop(message: Message) -> None:
    _cancel_requests.add(message.from_user.id)
    await message.answer("🛑 Stopping after the current send…")
