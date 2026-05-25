"""Combined admin router.

Each sub-flow lives in its own module. Order of inclusion matters:
the catch-all fallback in `common` must be registered LAST so
specific handlers get a chance to match first.
"""

from aiogram import Router

from . import (
    admins,
    broadcast,
    channels,
    main_menu,
    maintenance,
    settings,
    stats,
    users,
    common,
)

router = Router(name="admin_panel")
router.include_router(main_menu.router)
router.include_router(stats.router)
router.include_router(broadcast.router)
router.include_router(users.router)
router.include_router(settings.router)
router.include_router(admins.router)
router.include_router(channels.router)
router.include_router(maintenance.router)
router.include_router(common.router)  # fallback — must be last
