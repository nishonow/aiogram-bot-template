from aiogram.fsm.state import State, StatesGroup


class Admin(StatesGroup):
    main = State()
    stats = State()

    broadcast_input = State()
    broadcast_preview = State()
    broadcast_sending = State()

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
    maintenance_confirm = State()
    clear_users_confirm = State()
    action_log = State()
