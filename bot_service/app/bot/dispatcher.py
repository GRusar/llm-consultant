from aiogram import Bot, Dispatcher
from app.core.config import settings
from app.bot import handlers


def create_bot_and_dispatcher() -> tuple[Bot, Dispatcher]:
    bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(handlers.router)
    return bot, dp
