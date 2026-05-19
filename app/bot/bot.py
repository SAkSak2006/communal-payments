import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.types import ErrorEvent

from app.config import settings

logger = logging.getLogger(__name__)

bot: Bot | None = None
dp: Dispatcher | None = None
_polling_task: asyncio.Task | None = None


async def start_bot():
    global bot, dp, _polling_task

    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()

    # Register middleware
    from app.bot.middlewares.throttling import ThrottlingMiddleware
    from app.bot.middlewares.auth import AuthMiddleware

    dp.message.middleware(ThrottlingMiddleware(rate_limit=0.5))
    dp.message.middleware(AuthMiddleware())

    # Register routers
    from app.bot.handlers import start, readings, balance, payments, tariffs, profile
    from app.bot.handlers import help as help_handler

    dp.include_router(start.router)
    dp.include_router(readings.router)
    dp.include_router(balance.router)
    dp.include_router(payments.router)
    dp.include_router(tariffs.router)
    dp.include_router(profile.router)
    dp.include_router(help_handler.router)

    # Global error handler
    @dp.errors()
    async def error_handler(event: ErrorEvent):
        logger.error(f"Bot error: {event.exception}", exc_info=event.exception)
        try:
            if event.update.message:
                await event.update.message.answer(
                    "⚠️ Произошла ошибка. Попробуйте ещё раз или введите /cancel."
                )
            elif event.update.callback_query:
                await event.update.callback_query.answer(
                    "Произошла ошибка. Попробуйте ещё раз.", show_alert=True
                )
        except Exception:
            pass

    _polling_task = asyncio.create_task(dp.start_polling(bot))


async def stop_bot():
    global bot, dp, _polling_task
    if dp:
        await dp.stop_polling()
    if bot:
        await bot.session.close()
    if _polling_task:
        _polling_task.cancel()
