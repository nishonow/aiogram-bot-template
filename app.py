import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

from admin_panel import AdminMiddleware, admin_router, init_admin_tables
from config import BOT_TOKEN, LOG_LEVEL
from core.db import init_users_table
from handlers import start as start_handlers
from middlewares.ban_middleware import BanMiddleware
from middlewares.maintenance_middleware import MaintenanceMiddleware

logger = logging.getLogger(__name__)


async def set_bot_commands(bot: Bot) -> None:
    await bot.set_my_commands(
        [
            BotCommand(command="start", description="Start the bot"),
            BotCommand(command="admin", description="Open the admin panel"),
        ]
    )


async def main() -> None:
    logging.basicConfig(
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        level=LOG_LEVEL,
    )

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    # Admin panel: gate the entire router behind AdminMiddleware
    admin_router.message.middleware(AdminMiddleware())
    dp.include_router(admin_router)

    # User-facing routers: drop banned users, block during maintenance
    start_handlers.router.message.middleware(BanMiddleware())
    start_handlers.router.message.middleware(MaintenanceMiddleware())
    dp.include_router(start_handlers.router)

    await init_users_table()
    await init_admin_tables()
    await bot.delete_webhook(drop_pending_updates=True)
    await set_bot_commands(bot)

    logger.info("Bot starting up")
    try:
        await dp.start_polling(bot)
    finally:
        logger.info("Bot shutting down")
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.getLogger(__name__).info("Stopped by user")
