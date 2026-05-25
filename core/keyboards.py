from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder


def start_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.button(text="🎲 Random Fact")
    return builder.as_markup(resize_keyboard=True)


def admin_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📊 Statistics", callback_data="admin:stats")
    builder.button(text="📤 Broadcast", callback_data="admin:broadcast")
    builder.button(text="⚙️ Settings", callback_data="admin:settings")
    builder.adjust(1)
    return builder.as_markup()


def settings_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Add Admin", callback_data="admin:add_admin")
    builder.button(text="➖ Remove Admin", callback_data="admin:remove_admin")
    builder.button(text="➕ Add Channel", callback_data="admin:add_channel")
    builder.button(text="➖ Remove Channel", callback_data="admin:remove_channel")
    builder.button(text="🗑 Clear Users", callback_data="admin:clear_db")
    builder.button(text="⬅️ Back", callback_data="admin:menu")
    builder.adjust(2, 2, 1, 1)
    return builder.as_markup()


def stats_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🔄 Refresh", callback_data="admin:stats:refresh")
    builder.button(text="⬅️ Back", callback_data="admin:menu")
    builder.adjust(1)
    return builder.as_markup()


def cancel_to_menu_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Cancel", callback_data="admin:menu")
    return builder.as_markup()


def cancel_to_settings_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Cancel", callback_data="admin:settings")
    return builder.as_markup()


def back_to_settings_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Back", callback_data="admin:settings")
    return builder.as_markup()


def confirm_broadcast_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Send", callback_data="admin:broadcast:confirm")
    builder.button(text="🚫 Cancel", callback_data="admin:broadcast:cancel")
    return builder.as_markup()


def confirm_clear_db_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Yes, clear", callback_data="admin:clear_db:confirm")
    builder.button(text="❌ Cancel", callback_data="admin:settings")
    return builder.as_markup()
