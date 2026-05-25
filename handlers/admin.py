import asyncio
import logging
import time

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError, TelegramForbiddenError
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from core.db import (
    add_admin,
    add_channel,
    clear_db,
    count_admins,
    count_new_users_last_24_hours,
    count_users,
    get_admin_details,
    get_admins,
    get_channel_ids,
    get_user_ids,
    remove_admin,
    remove_channel,
)
from core.keyboards import (
    admin_keyboard,
    back_to_settings_keyboard,
    cancel_to_menu_keyboard,
    cancel_to_settings_keyboard,
    confirm_broadcast_keyboard,
    confirm_clear_db_keyboard,
    settings_keyboard,
    stats_keyboard,
)
from utils.consts import BOT_START_TIME
from utils.helpers import get_channel_name, get_channel_username

logger = logging.getLogger(__name__)
router = Router()

BROADCAST_DELAY = 0.05  # seconds between sends (~20 msg/s, under Telegram's limit)


class BroadcastState(StatesGroup):
    get_message = State()
    get_action = State()


class AdminManagementState(StatesGroup):
    add_admin = State()
    remove_admin = State()


class ChannelManagementState(StatesGroup):
    add_channel = State()
    remove_channel = State()


# ---------- shared renderers ----------

async def _render_admin_list() -> str:
    details = await get_admin_details()
    by_id = {tg_id: name for tg_id, name in details}
    all_ids = await get_admins()
    if not all_ids:
        return "_No runtime admins yet._"
    lines = []
    for admin_id in all_ids:
        name = by_id.get(admin_id) or "Unknown"
        lines.append(f"[{admin_id}](tg://user?id={admin_id}) — {name}")
    return "\n".join(lines)


async def _render_channel_list(bot: Bot) -> str:
    channels = await get_channel_ids()
    if not channels:
        return "_No required channels._"
    lines = []
    for channel_id in channels:
        username = await get_channel_username(bot, channel_id)
        if username:
            lines.append(f"@{username} ({channel_id})")
        else:
            lines.append(f"{channel_id}")
    return "\n".join(lines)


async def _settings_text() -> str:
    admin_list = await _render_admin_list()
    return f"⚙️ *Settings*\n\n*Runtime admins:*\n{admin_list}"


def _format_uptime() -> str:
    seconds = int(time.time() - BOT_START_TIME)
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, secs = divmod(rem, 60)
    return f"{days}d {hours}h {minutes}m {secs}s"


async def _stats_text() -> str:
    total_users = await count_users()
    new_users = await count_new_users_last_24_hours()
    total_admins = await count_admins()
    return (
        f"📊 *Statistics*\n\n"
        f"👤 Total users: *{total_users}*\n"
        f"🆕 New (24h): *{new_users}*\n"
        f"👑 Admins: *{total_admins}*\n"
        f"🕒 Uptime: `{_format_uptime()}`"
    )


# ---------- main menu ----------

@router.message(Command("admin"))
async def admin_command(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        "👑 *Admin Panel*\n\nChoose an action:",
        reply_markup=admin_keyboard(),
        parse_mode="Markdown",
    )


@router.callback_query(F.data == "admin:menu")
async def admin_menu_handler(call: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await call.message.edit_text(
        "👑 *Admin Panel*\n\nChoose an action:",
        reply_markup=admin_keyboard(),
        parse_mode="Markdown",
    )
    await call.answer()


# ---------- stats ----------

@router.callback_query(F.data == "admin:stats")
async def stats_handler(call: CallbackQuery) -> None:
    await call.message.edit_text(
        await _stats_text(),
        reply_markup=stats_keyboard(),
        parse_mode="Markdown",
    )
    await call.answer()


@router.callback_query(F.data == "admin:stats:refresh")
async def stats_refresh_handler(call: CallbackQuery) -> None:
    try:
        await call.message.edit_text(
            await _stats_text(),
            reply_markup=stats_keyboard(),
            parse_mode="Markdown",
        )
    except TelegramAPIError:
        # message content identical; ignore "message is not modified"
        pass
    await call.answer("Refreshed")


# ---------- broadcast ----------

@router.callback_query(F.data == "admin:broadcast")
async def broadcast_prompt(call: CallbackQuery, state: FSMContext) -> None:
    msg = await call.message.edit_text(
        "✍️ Send the message you want to broadcast.\n\n"
        "Any message type works (text, photo, video, document, etc.).",
        reply_markup=cancel_to_menu_keyboard(),
    )
    await state.set_state(BroadcastState.get_message)
    await state.update_data(prompt_id=msg.message_id)
    await call.answer()


@router.message(BroadcastState.get_message)
async def broadcast_get_message(message: Message, state: FSMContext, bot: Bot) -> None:
    data = await state.get_data()
    prompt_id = data.get("prompt_id")
    if prompt_id:
        try:
            await bot.edit_message_reply_markup(
                chat_id=message.chat.id, message_id=prompt_id, reply_markup=None
            )
        except TelegramAPIError:
            pass

    await bot.copy_message(
        chat_id=message.chat.id,
        from_chat_id=message.chat.id,
        message_id=message.message_id,
    )
    await message.answer(
        "👆 This is what users will receive. Send it?",
        reply_markup=confirm_broadcast_keyboard(),
    )
    await state.update_data(source_chat_id=message.chat.id, source_message_id=message.message_id)
    await state.set_state(BroadcastState.get_action)


@router.callback_query(F.data == "admin:broadcast:confirm", BroadcastState.get_action)
async def broadcast_confirm(call: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    data = await state.get_data()
    source_chat_id = data.get("source_chat_id")
    source_message_id = data.get("source_message_id")
    await state.clear()

    if not source_chat_id or not source_message_id:
        await call.message.edit_text("⚠️ Broadcast source lost. Please try again.", reply_markup=admin_keyboard())
        await call.answer()
        return

    user_ids = await get_user_ids()
    total = len(user_ids)
    if total == 0:
        await call.message.edit_text("ℹ️ No users to broadcast to.", reply_markup=admin_keyboard())
        await call.answer()
        return

    progress = await call.message.edit_text(f"📤 Sending to {total} users…")
    sent = 0
    blocked = 0
    failed = 0

    for index, user_id in enumerate(user_ids, start=1):
        try:
            await bot.copy_message(
                chat_id=user_id,
                from_chat_id=source_chat_id,
                message_id=source_message_id,
            )
            sent += 1
        except TelegramForbiddenError:
            blocked += 1
        except TelegramAPIError as exc:
            failed += 1
            logger.warning("Broadcast to %s failed: %s", user_id, exc)

        if index % 25 == 0 or index == total:
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

    await progress.edit_text(
        f"✅ *Broadcast complete*\n\n"
        f"Recipients: *{total}*\n"
        f"✅ Sent: *{sent}*\n"
        f"🚫 Blocked: *{blocked}*\n"
        f"⚠️ Failed: *{failed}*",
        reply_markup=admin_keyboard(),
        parse_mode="Markdown",
    )
    await call.answer()


@router.callback_query(F.data == "admin:broadcast:cancel", BroadcastState.get_action)
async def broadcast_cancel(call: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await call.message.edit_text(
        "🚫 Broadcast cancelled.",
        reply_markup=admin_keyboard(),
    )
    await call.answer()


# ---------- settings ----------

@router.callback_query(F.data == "admin:settings")
async def settings_handler(call: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await call.message.edit_text(
        await _settings_text(),
        reply_markup=settings_keyboard(),
        parse_mode="Markdown",
    )
    await call.answer()


# ---------- add / remove admin ----------

@router.callback_query(F.data == "admin:add_admin")
async def add_admin_prompt(call: CallbackQuery, state: FSMContext) -> None:
    text = (
        "📝 Send the Telegram ID of the user to grant admin access.\n\n"
        f"*Current admins:*\n{await _render_admin_list()}"
    )
    msg = await call.message.edit_text(
        text, reply_markup=cancel_to_settings_keyboard(), parse_mode="Markdown"
    )
    await state.update_data(prompt_id=msg.message_id)
    await state.set_state(AdminManagementState.add_admin)
    await call.answer()


@router.message(AdminManagementState.add_admin)
async def add_admin_input(message: Message, state: FSMContext) -> None:
    await state.clear()
    try:
        new_admin = int(message.text.strip())
    except (ValueError, AttributeError):
        await message.answer(
            "❌ Invalid Telegram ID. Send a numeric ID.",
            reply_markup=back_to_settings_keyboard(),
        )
        return

    if new_admin in await get_admins():
        await message.answer(
            "⚠️ This user is already an admin.",
            reply_markup=back_to_settings_keyboard(),
        )
        return

    await add_admin(new_admin)
    await message.answer(
        f"✅ User `{new_admin}` has been added as an admin.",
        reply_markup=back_to_settings_keyboard(),
        parse_mode="Markdown",
    )


@router.callback_query(F.data == "admin:remove_admin")
async def remove_admin_prompt(call: CallbackQuery, state: FSMContext) -> None:
    text = (
        "📝 Send the Telegram ID of the admin to remove.\n\n"
        f"*Current admins:*\n{await _render_admin_list()}"
    )
    msg = await call.message.edit_text(
        text, reply_markup=cancel_to_settings_keyboard(), parse_mode="Markdown"
    )
    await state.update_data(prompt_id=msg.message_id)
    await state.set_state(AdminManagementState.remove_admin)
    await call.answer()


@router.message(AdminManagementState.remove_admin)
async def remove_admin_input(message: Message, state: FSMContext) -> None:
    await state.clear()
    try:
        target = int(message.text.strip())
    except (ValueError, AttributeError):
        await message.answer(
            "❌ Invalid Telegram ID. Send a numeric ID.",
            reply_markup=back_to_settings_keyboard(),
        )
        return

    if target not in await get_admins():
        await message.answer(
            "⚠️ This user is not an admin.",
            reply_markup=back_to_settings_keyboard(),
        )
        return

    await remove_admin(target)
    await message.answer(
        f"✅ User `{target}` removed from admins.",
        reply_markup=back_to_settings_keyboard(),
        parse_mode="Markdown",
    )


# ---------- add / remove channel ----------

@router.callback_query(F.data == "admin:add_channel")
async def add_channel_prompt(call: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    text = (
        "📝 Send the channel to require users to join.\n\n"
        "Format: `@channel_username` or numeric channel ID (e.g. `-1001234567890`).\n"
        "The bot must be a member of the channel.\n\n"
        f"*Current required channels:*\n{await _render_channel_list(bot)}"
    )
    msg = await call.message.edit_text(
        text, reply_markup=cancel_to_settings_keyboard(), parse_mode="Markdown"
    )
    await state.update_data(prompt_id=msg.message_id)
    await state.set_state(ChannelManagementState.add_channel)
    await call.answer()


@router.message(ChannelManagementState.add_channel)
async def add_channel_input(message: Message, state: FSMContext, bot: Bot) -> None:
    await state.clear()
    new_channel = (message.text or "").strip()
    if not new_channel:
        await message.answer(
            "❌ Empty input. Send a channel username or ID.",
            reply_markup=back_to_settings_keyboard(),
        )
        return

    if new_channel in await get_channel_ids():
        await message.answer(
            "⚠️ This channel is already required.",
            reply_markup=back_to_settings_keyboard(),
        )
        return

    name = await get_channel_name(bot, new_channel)
    if name is None:
        await message.answer(
            "❌ Couldn't access that channel. Make sure the bot is a member and the ID is correct.",
            reply_markup=back_to_settings_keyboard(),
        )
        return

    await add_channel(new_channel)
    await message.answer(
        f"✅ Channel *{name}* added.",
        reply_markup=back_to_settings_keyboard(),
        parse_mode="Markdown",
    )


@router.callback_query(F.data == "admin:remove_channel")
async def remove_channel_prompt(call: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    text = (
        "📝 Send the channel username or ID to remove.\n\n"
        f"*Current required channels:*\n{await _render_channel_list(bot)}"
    )
    msg = await call.message.edit_text(
        text, reply_markup=cancel_to_settings_keyboard(), parse_mode="Markdown"
    )
    await state.update_data(prompt_id=msg.message_id)
    await state.set_state(ChannelManagementState.remove_channel)
    await call.answer()


@router.message(ChannelManagementState.remove_channel)
async def remove_channel_input(message: Message, state: FSMContext) -> None:
    await state.clear()
    target = (message.text or "").strip()
    if target not in await get_channel_ids():
        await message.answer(
            "⚠️ This channel isn't in the list.",
            reply_markup=back_to_settings_keyboard(),
        )
        return

    await remove_channel(target)
    await message.answer(
        f"✅ Channel `{target}` removed.",
        reply_markup=back_to_settings_keyboard(),
        parse_mode="Markdown",
    )


# ---------- clear users ----------

@router.callback_query(F.data == "admin:clear_db")
async def clear_db_prompt(call: CallbackQuery) -> None:
    await call.message.edit_text(
        "⚠️ *Clear the users table?*\n\n"
        "This deletes every registered user from the database. "
        "Admins and channels are kept. This cannot be undone.",
        reply_markup=confirm_clear_db_keyboard(),
        parse_mode="Markdown",
    )
    await call.answer()


@router.callback_query(F.data == "admin:clear_db:confirm")
async def clear_db_confirm(call: CallbackQuery) -> None:
    await clear_db()
    await call.message.edit_text(
        "🗑 Users table cleared.",
        reply_markup=back_to_settings_keyboard(),
    )
    await call.answer()
