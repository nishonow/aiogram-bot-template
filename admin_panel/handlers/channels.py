"""Add / remove required-join channels."""

import html

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from admin_panel import keyboards as kb
from admin_panel import texts as T
from admin_panel.db import add_channel, get_channel_ids, log_action, remove_channel
from admin_panel.states import Admin

router = Router(name="admin_channels")


async def _channels_text() -> str:
    channels = await get_channel_ids()
    body = "\n".join(f"• <code>{html.escape(c)}</code>" for c in channels) or "<i>None</i>"
    return f"{T.TITLE_CHANNELS}\n\n{body}"


# ---- menu ----

@router.message(Admin.settings, F.text == T.BTN_CHANNELS)
async def open_channels(message: Message, state: FSMContext) -> None:
    await state.set_state(Admin.channels_menu)
    await message.answer(await _channels_text(), reply_markup=kb.channels_menu(), parse_mode="HTML")


@router.message(Admin.channels_menu, F.text == T.BTN_BACK)
async def channels_back(message: Message, state: FSMContext) -> None:
    await state.set_state(Admin.settings)
    await message.answer(T.TITLE_SETTINGS, reply_markup=kb.settings_menu(), parse_mode="HTML")


# ---- add ----

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
    await message.answer(await _channels_text(), reply_markup=kb.channels_menu(), parse_mode="HTML")


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


# ---- remove ----

@router.message(Admin.channels_menu, F.text == T.BTN_REMOVE_CHANNEL)
async def channel_remove_prompt(message: Message, state: FSMContext) -> None:
    await state.set_state(Admin.channel_remove_input)
    await message.answer("Send the channel username or ID to remove:", reply_markup=kb.cancel_kb())


@router.message(Admin.channel_remove_input, F.text == T.BTN_CANCEL)
async def channel_remove_cancel(message: Message, state: FSMContext) -> None:
    await state.set_state(Admin.channels_menu)
    await message.answer(await _channels_text(), reply_markup=kb.channels_menu(), parse_mode="HTML")


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
