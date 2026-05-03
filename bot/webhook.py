"""
bot/webhook.py — Webhook endpoint для production.
Принимает updates от Telegram и передаёт в Dispatcher.
Верифицирует подпись через X-Telegram-Bot-Api-Secret-Token.
"""

from __future__ import annotations
import hashlib
import hmac
import logging
import os

from aiogram.types import Update
from fastapi import APIRouter, Header, HTTPException, Request

from bot.main import create_bot, create_dispatcher

logger = logging.getLogger(__name__)

WEBHOOK_SECRET = os.getenv("TELEGRAM_WEBHOOK_SECRET", "")

webhook_router = APIRouter()

# Singleton — создаём один раз при первом запросе
_bot = None
_dp = None


def get_bot_and_dp():
    global _bot, _dp
    if _bot is None:
        _bot = create_bot()
        _dp = create_dispatcher()
    return _bot, _dp


@webhook_router.post("/webhook")
async def handle_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str = Header(default=""),
) -> dict:
    """
    Принимает Telegram Update и передаёт в aiogram Dispatcher.
    Проверяет secret token для защиты от посторонних запросов.
    """
    # Верификация подписи
    if WEBHOOK_SECRET and x_telegram_bot_api_secret_token != WEBHOOK_SECRET:
        logger.warning("[Webhook] Invalid secret token")
        raise HTTPException(status_code=403, detail="Forbidden")

    bot, dp = get_bot_and_dp()

    try:
        body = await request.json()
        update = Update(**body)
        await dp.feed_update(bot=bot, update=update)
    except Exception as e:
        logger.exception(f"[Webhook] Error processing update: {e}")
        # Возвращаем 200 чтобы Telegram не ретраил
    
    return {"ok": True}


@webhook_router.get("/webhook/info")
async def webhook_info() -> dict:
    """Возвращает информацию о текущем webhook (только для dev)."""
    if os.getenv("APP_ENV") == "production":
        raise HTTPException(status_code=404)
    
    bot, _ = get_bot_and_dp()
    info = await bot.get_webhook_info()
    return {
        "url": info.url,
        "pending_update_count": info.pending_update_count,
        "last_error_message": info.last_error_message,
    }
