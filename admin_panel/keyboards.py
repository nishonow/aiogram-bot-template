from aiogram.types import InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

from admin_panel import texts as T


# ============================================================
# reply keyboards (menu navigation — persistent at chat bottom)
# ============================================================

def _kb(rows: list[list[str]]) -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    sizes: list[int] = []
    for row in rows:
        for label in row:
            builder.button(text=label)
        sizes.append(len(row))
    builder.adjust(*sizes)
    return builder.as_markup(resize_keyboard=True)


def main_menu() -> ReplyKeyboardMarkup:
    return _kb([
        [T.BTN_STATS, T.BTN_BROADCAST],
        [T.BTN_USERS, T.BTN_SETTINGS],
        [T.BTN_EXIT],
    ])


def cancel_kb() -> ReplyKeyboardMarkup:
    return _kb([[T.BTN_CANCEL]])


def users_menu() -> ReplyKeyboardMarkup:
    return _kb([
        [T.BTN_USER_FIND],
        [T.BTN_USER_BAN, T.BTN_USER_UNBAN],
        [T.BTN_BACK],
    ])


def settings_menu() -> ReplyKeyboardMarkup:
    return _kb([
        [T.BTN_ADMINS, T.BTN_CHANNELS],
        [T.BTN_MAINTENANCE, T.BTN_ACTION_LOG],
        [T.BTN_BACKUP, T.BTN_CLEAR_USERS],
        [T.BTN_BACK],
    ])


def admins_menu() -> ReplyKeyboardMarkup:
    return _kb([
        [T.BTN_ADD_ADMIN, T.BTN_REMOVE_ADMIN],
        [T.BTN_BACK],
    ])


def channels_menu() -> ReplyKeyboardMarkup:
    return _kb([
        [T.BTN_ADD_CHANNEL, T.BTN_REMOVE_CHANNEL],
        [T.BTN_BACK],
    ])


def remove_kb() -> ReplyKeyboardRemove:
    return ReplyKeyboardRemove()


# ============================================================
# inline keyboards (action on a specific message)
# ============================================================

def stats_inline() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=T.BTN_INLINE_REFRESH, callback_data="admin:stats:refresh")
    b.button(text=T.BTN_INLINE_CLOSE, callback_data="admin:close")
    b.adjust(2)
    return b.as_markup()


def maintenance_inline(currently_on: bool) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    label = T.BTN_MAINT_TURN_OFF if currently_on else T.BTN_MAINT_TURN_ON
    b.button(text=label, callback_data="admin:maint:toggle")
    b.button(text=T.BTN_INLINE_CLOSE, callback_data="admin:close")
    b.adjust(1)
    return b.as_markup()


def clear_users_inline() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=T.BTN_INLINE_YES, callback_data="admin:clear:yes")
    b.button(text=T.BTN_INLINE_NO, callback_data="admin:close")
    return b.as_markup()


def broadcast_preview_inline() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=T.BTN_BROADCAST_SEND, callback_data="admin:bc:send")
    b.button(text=T.BTN_BROADCAST_EDIT, callback_data="admin:bc:edit")
    b.button(text=T.BTN_BROADCAST_CANCEL, callback_data="admin:bc:cancel")
    b.adjust(1, 2)
    return b.as_markup()


def broadcast_stop_inline() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=T.BTN_BROADCAST_STOP, callback_data="admin:bc:stop")
    return b.as_markup()


def user_actions_inline(tg_id: int, is_banned: bool) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    if is_banned:
        b.button(text=T.BTN_USER_UNBAN_INLINE, callback_data=f"admin:user:unban:{tg_id}")
    else:
        b.button(text=T.BTN_USER_BAN_INLINE, callback_data=f"admin:user:ban:{tg_id}")
    b.button(text=T.BTN_INLINE_CLOSE, callback_data="admin:close")
    return b.as_markup()
