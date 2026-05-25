import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

import handlers
from config import BOT_TOKEN, LOG_LEVEL
from core.db import on_startup
from middlewares.admin_middleware import AdminMiddleware

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

    handlers.admin.router.message.middleware(AdminMiddleware())
    handlers.admin.router.callback_query.middleware(AdminMiddleware())

    dp.include_router(handlers.start.router)
    dp.include_router(handlers.admin.router)

    await on_startup()
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
