"""
notifications/sender.py — Сервис отправки уведомлений.
Используется Celery-задачами и прямыми вызовами из сервисов.
"""

from __future__ import annotations
import logging
import os

import httpx

logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TG_API = f"https://api.telegram.org/bot{BOT_TOKEN}"


async def send_message_async(
    telegram_id: int,
    text: str,
    parse_mode: str = "Markdown",
    reply_markup: dict | None = None,
) -> bool:
    """Асинхронная отправка сообщения пользователю."""
    payload: dict = {
        "chat_id": telegram_id,
        "text": text,
        "parse_mode": parse_mode,
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(f"{TG_API}/sendMessage", json=payload)
            return resp.is_success
    except Exception as e:
        logger.warning(f"[Sender] Failed to send to {telegram_id}: {e}")
        return False


def send_message_sync(
    telegram_id: int,
    text: str,
    parse_mode: str = "Markdown",
) -> bool:
    """Синхронная отправка (для Celery tasks)."""
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(f"{TG_API}/sendMessage", json={
                "chat_id": telegram_id,
                "text": text,
                "parse_mode": parse_mode,
            })
            return resp.is_success
    except Exception as e:
        logger.warning(f"[Sender] Sync send failed to {telegram_id}: {e}")
        return False


async def send_photo_async(
    telegram_id: int,
    photo_url: str,
    caption: str | None = None,
) -> bool:
    """Асинхронная отправка фото пользователю."""
    payload: dict = {"chat_id": telegram_id, "photo": photo_url}
    if caption:
        payload["caption"] = caption
        payload["parse_mode"] = "Markdown"

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(f"{TG_API}/sendPhoto", json=payload)
            return resp.is_success
    except Exception as e:
        logger.warning(f"[Sender] Photo send failed to {telegram_id}: {e}")
        return False


async def notify_user(
    user_id: str,
    text: str,
    parse_mode: str = "Markdown",
) -> bool:
    """
    Удобная обёртка: отправляет уведомление по UUID пользователя.
    Получает telegram_id из Supabase.
    """
    from infra.db.supabase import supabase_admin
    res = (
        supabase_admin.table("users")
        .select("telegram_id")
        .eq("id", user_id)
        .maybe_single()
        .execute()
    )
    if not res.data:
        return False
    return await send_message_async(res.data["telegram_id"], text, parse_mode)
