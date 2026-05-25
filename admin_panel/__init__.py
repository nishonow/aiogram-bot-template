"""Drop-in admin panel for any aiogram bot.

Wire it up in your bot:

    from admin_panel import admin_router, AdminMiddleware, init_admin_tables

    admin_router.message.middleware(AdminMiddleware())
    dp.include_router(admin_router)
    await init_admin_tables()  # at startup

The panel assumes a `users` table with `telegram_id`, `name`, `username`,
`created_at` columns. Adapt `admin_panel/db.py` if your schema differs.
"""

from admin_panel.db import init_admin_tables
from admin_panel.handlers import router as admin_router
from admin_panel.middleware import AdminMiddleware

__all__ = ["admin_router", "AdminMiddleware", "init_admin_tables"]
