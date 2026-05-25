"""All admin-panel button labels and prompt strings in one place.

Edit these to localize or rebrand the panel.
"""

# ---- main menu ----
BTN_STATS = "📊 Stats"
BTN_BROADCAST = "📤 Broadcast"
BTN_USERS = "👥 Users"
BTN_SETTINGS = "⚙️ Settings"
BTN_EXIT = "🚪 Exit"

# ---- navigation ----
BTN_BACK = "⬅️ Back"
BTN_CANCEL = "❌ Cancel"
BTN_REFRESH = "🔄 Refresh"
BTN_CONFIRM_YES = "✅ Yes"
BTN_CONFIRM_NO = "❌ No"

# ---- broadcast ----
BTN_BROADCAST_SEND = "✅ Send to all"
BTN_BROADCAST_TEST = "🧪 Send to me"
BTN_BROADCAST_EDIT = "✏️ Edit"
BTN_BROADCAST_STOP = "🛑 Stop broadcast"

# ---- users ----
BTN_USER_FIND = "🔍 Find user"
BTN_USER_LIST = "📋 List users"
BTN_USER_BAN = "🚫 Ban user"
BTN_USER_UNBAN = "✅ Unban user"
BTN_USER_EXPORT = "📥 Export CSV"
BTN_PAGE_PREV = "⬅️ Prev"
BTN_PAGE_NEXT = "Next ➡️"
BTN_PAGE_INFO = "•"  # informational, no-op

# ---- settings ----
BTN_ADMINS = "👑 Admins"
BTN_CHANNELS = "📢 Required channels"
BTN_MAINTENANCE = "🔧 Maintenance mode"
BTN_BACKUP = "💾 Download DB backup"
BTN_CLEAR_USERS = "🗑 Clear users"
BTN_ACTION_LOG = "📜 Action log"

BTN_ADD_ADMIN = "➕ Add admin"
BTN_REMOVE_ADMIN = "➖ Remove admin"
BTN_ADD_CHANNEL = "➕ Add channel"
BTN_REMOVE_CHANNEL = "➖ Remove channel"

# ---- titles ----
TITLE_MAIN = "👑 <b>Admin Panel</b>\n\nChoose an action:"
TITLE_STATS = "📊 <b>Statistics</b>"
TITLE_BROADCAST_PROMPT = (
    "✍️ Send the message you want to broadcast.\n\n"
    "Any message type works (text, photo, video, document, sticker, ...)."
)
TITLE_BROADCAST_PREVIEW = "👆 This is what users will receive. Choose an action:"
TITLE_USERS = "👥 <b>Users</b>"
TITLE_SETTINGS = "⚙️ <b>Settings</b>"
TITLE_ADMINS = "👑 <b>Admins</b>"
TITLE_CHANNELS = "📢 <b>Required channels</b>"
TITLE_MAINTENANCE = "🔧 <b>Maintenance mode</b>"
TITLE_ACTION_LOG = "📜 <b>Recent admin actions</b>"

MSG_EXIT = "Admin panel closed."
MSG_NOT_AUTHORIZED = "🚫 You are not authorized to use this command."
MSG_CANCELLED = "Cancelled."
MSG_MAINTENANCE_ON = (
    "🔧 The bot is currently under maintenance. Please try again later."
)
MSG_BANNED = "🚫 You have been banned from using this bot."

# ---- placeholders used in format() calls; keep names intact ----
MSG_USER_INFO = (
    "<b>User info</b>\n\n"
    "ID: <code>{id}</code>\n"
    "Name: {name}\n"
    "Username: {username}\n"
    "Joined: {joined}\n"
    "Admin: {is_admin}\n"
    "Banned: {is_banned}"
)
