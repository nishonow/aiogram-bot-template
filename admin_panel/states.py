from aiogram.fsm.state import State, StatesGroup


class Admin(StatesGroup):
    main = State()

    broadcast_input = State()
    broadcast_preview = State()

    users = State()
    user_find_input = State()
    user_ban_input = State()
    user_unban_input = State()

    settings = State()
    admins_menu = State()
    admin_add_input = State()
    admin_remove_input = State()
    channels_menu = State()
    channel_add_input = State()
    channel_remove_input = State()
