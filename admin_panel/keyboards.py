from aiogram.types import ReplyKeyboardMarkup, ReplyKeyboardRemove
from aiogram.utils.keyboard import ReplyKeyboardBuilder

from admin_panel import texts as T


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


def stats_kb() -> ReplyKeyboardMarkup:
    return _kb([[T.BTN_REFRESH], [T.BTN_BACK]])


def cancel_kb() -> ReplyKeyboardMarkup:
    return _kb([[T.BTN_CANCEL]])


def broadcast_preview_kb() -> ReplyKeyboardMarkup:
    return _kb([
        [T.BTN_BROADCAST_SEND, T.BTN_BROADCAST_TEST],
        [T.BTN_BROADCAST_EDIT, T.BTN_CANCEL],
    ])


def broadcast_running_kb() -> ReplyKeyboardMarkup:
    return _kb([[T.BTN_BROADCAST_STOP]])


def users_menu() -> ReplyKeyboardMarkup:
    return _kb([
        [T.BTN_USER_FIND, T.BTN_USER_LIST],
        [T.BTN_USER_BAN, T.BTN_USER_UNBAN],
        [T.BTN_USER_EXPORT],
        [T.BTN_BACK],
    ])


def users_list_kb() -> ReplyKeyboardMarkup:
    return _kb([
        [T.BTN_PAGE_PREV, T.BTN_PAGE_NEXT],
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


def confirm_kb() -> ReplyKeyboardMarkup:
    return _kb([[T.BTN_CONFIRM_YES, T.BTN_CONFIRM_NO]])


def remove_kb() -> ReplyKeyboardRemove:
    return ReplyKeyboardRemove()
