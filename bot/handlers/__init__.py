from aiogram import Dispatcher

from bot.handlers.start import router as start_router
from bot.handlers.profile import router as profile_router
from bot.handlers.plans import router as plans_router
from bot.handlers.payment import router as payment_router
from bot.handlers.support import router as support_router
from bot.handlers.admin import router as admin_router


def register_handlers(dp: Dispatcher) -> None:
    dp.include_router(start_router)
    dp.include_router(profile_router)
    dp.include_router(plans_router)
    dp.include_router(payment_router)
    dp.include_router(support_router)
    dp.include_router(admin_router)
