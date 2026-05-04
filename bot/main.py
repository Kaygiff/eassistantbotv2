"""
bot/main.py — Точка входа Telegram бота.
Инициализирует aiogram, регистрирует роутеры, запускает webhook или polling.
"""

from __future__ import annotations
import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from infra.monitoring.metrics import init_sentry, init_logging
from bot.brain.dispatcher import register_all_handlers
from bot.brain.editor import load_rules_into_classifier
from infra.safety.content_moderation import load_stopwords
from bot.handlers.private import private_router
from bot.handlers.group import group_router
from bot.handlers.callbacks import callback_router

logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEBHOOK_URL = os.getenv("TELEGRAM_WEBHOOK_URL")
WEBHOOK_SECRET = os.getenv("TELEGRAM_WEBHOOK_SECRET", "")
APP_ENV = os.getenv("APP_ENV", "development")


async def on_startup(bot: Bot) -> None:
    """Вызывается при старте бота."""
    logger.info("[Bot] Starting up...")

    # Регистрируем все хэндлеры Brain
    register_all_handlers()

    # Загружаем кастомные правила Brain Editor
    count = await load_rules_into_classifier()
    logger.info(f"[Bot] Loaded {count} custom brain rules")

    # Загружаем стоп-слова для модерации
    await load_stopwords()

    if APP_ENV == "production" and WEBHOOK_URL:
        await bot.set_webhook(
            url=f"{WEBHOOK_URL}/webhook",
            secret_token=WEBHOOK_SECRET,
            drop_pending_updates=True,
        )
        logger.info(f"[Bot] Webhook set: {WEBHOOK_URL}/webhook")
    else:
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("[Bot] Webhook deleted (polling mode)")


async def on_shutdown(bot: Bot) -> None:
    """Вызывается при остановке бота."""
    logger.info("[Bot] Shutting down...")
    if APP_ENV == "production":
        await bot.delete_webhook()


def create_bot() -> Bot:
    """Создаёт экземпляр Bot."""
    if not BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN is not set")
    return Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN),
    )


def create_dispatcher() -> Dispatcher:
    """Создаёт Dispatcher и подключает роутеры."""
    dp = Dispatcher()

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    # Порядок важен: callbacks → private → group
    dp.include_router(callback_router)
    dp.include_router(private_router)
    dp.include_router(group_router)

    return dp


async def run_polling() -> None:
    """Запуск в режиме polling (dev)."""
    init_logging()
    init_sentry()

    bot = create_bot()
    dp = create_dispatcher()

    logger.info("[Bot] Starting polling...")
    await dp.start_polling(bot, allowed_updates=["message", "callback_query", "chat_member"])


if __name__ == "__main__":
    asyncio.run(run_polling())
