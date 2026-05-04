"""
services/ai_chat/chat.py — AI-чат с историей и персонализацией.
История: последние 20 сообщений в Redis + полная в Supabase.
"""

from __future__ import annotations
import json
import time
import logging

from infra.db.redis import get_redis, chat_history_key
from infra.db.supabase import supabase_admin
from services.ai_provider.hub import get_hub

logger = logging.getLogger(__name__)

MAX_REDIS_HISTORY = 20  # сообщений в Redis (быстрый контекст)


def _build_system_prompt(assistant_name: str, language: str) -> str:
    lang_names = {
        "ru": "русском", "kz": "казахском", "uz": "узбекском",
        "tj": "таджикском", "tm": "туркменском", "kg": "кыргызском",
        "by": "белорусском", "en": "English",
    }
    lang_label = lang_names.get(language, "русском")
    return (
        f"Ты {assistant_name} — дружелюбный и умный AI-ассистент в Telegram. "
        f"Отвечай на {lang_label} языке. "
        f"Будь естественным, кратким, полезным. "
        f"Не представляйся как GPT или OpenAI."
    )


async def get_redis_history(user_id: str) -> list[dict]:
    """Загружает последние 20 сообщений из Redis."""
    redis = get_redis()
    raw = await redis.get(chat_history_key(user_id))
    if raw:
        return json.loads(raw)
    return []


async def save_to_redis(user_id: str, history: list[dict]) -> None:
    """Сохраняет историю в Redis (обрезает до 20 сообщений)."""
    redis = get_redis()
    trimmed = history[-MAX_REDIS_HISTORY:]
    await redis.set(chat_history_key(user_id), json.dumps(trimmed, ensure_ascii=False))


async def save_to_supabase(user_id: str, role: str, content: str, model: str | None, tokens: int | None, ms: int | None) -> None:
    """Сохраняет сообщение в полную историю Supabase."""
    try:
        supabase_admin.table("chat_messages").insert({
            "user_id": user_id,
            "role": role,
            "content": content,
            "model_used": model,
            "tokens_used": tokens,
            "response_ms": ms,
        }).execute()
    except Exception as e:
        logger.warning(f"[AIChat] Failed to save to Supabase: {e}")


async def get_ai_response(
    user_id: str,
    user_message: str,
    language: str = "ru",
    assistant_name: str = "Ассистент",
) -> str:
    """
    Главная функция AI-чата.
    1. Загружает историю из Redis
    2. Добавляет новое сообщение
    3. Отправляет в AI Hub
    4. Сохраняет ответ в Redis + Supabase
    5. Возвращает текст ответа
    """
    history = await get_redis_history(user_id)

    # Добавляем новое сообщение пользователя
    history.append({"role": "user", "content": user_message})

    system = _build_system_prompt(assistant_name, language)
    hub = get_hub()

    start = time.monotonic()
    try:
        response_text, provider_name = await hub.chat(
            messages=history,
            system=system,
            max_tokens=1000,
            temperature=0.7,
        )
    except RuntimeError as e:
        logger.error(f"[AIChat] All providers failed: {e}")
        from core.i18n.loader import t
        return t(language, "common.error")

    elapsed_ms = round((time.monotonic() - start) * 1000)

    # Добавляем ответ ассистента в историю
    history.append({"role": "assistant", "content": response_text})

    # Сохраняем в Redis
    await save_to_redis(user_id, history)

    # Сохраняем в Supabase асинхронно (не блокируем ответ)
    import asyncio
    asyncio.create_task(save_to_supabase(user_id, "user", user_message, None, None, None))
    asyncio.create_task(save_to_supabase(user_id, "assistant", response_text, provider_name, None, elapsed_ms))

    return response_text


async def clear_history(user_id: str) -> None:
    """Очищает историю чата (Redis + не трогает Supabase)."""
    redis = get_redis()
    await redis.delete(chat_history_key(user_id))


async def get_full_history(user_id: str, limit: int = 50) -> list[dict]:
    """Полная история из Supabase (для EAdmin и экспорта)."""
    res = (
        supabase_admin.table("chat_messages")
        .select("*")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return list(reversed(res.data or []))
