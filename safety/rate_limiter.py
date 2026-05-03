"""
safety/rate_limiter.py — Rate limiting на базе Redis.
Защита от флуда и спама. Работает автоматически по умолчанию.
Тонкая настройка — через админпанель.
"""

from __future__ import annotations
import os
from typing import Optional

from db.redis import get_redis, rate_limit_key

# Дефолтные лимиты (можно переопределить через env или Feature Flags)
DEFAULT_LIMITS = {
    "message": (int(os.getenv("RATE_LIMIT_MESSAGES_PER_MINUTE", 30)), 60),   # 30 сообщений / 60 сек
    "ai_chat": (int(os.getenv("RATE_LIMIT_AI_PER_MINUTE", 10)), 60),         # 10 AI-запросов / 60 сек
    "casino":  (20, 60),     # 20 ставок / 60 сек
    "transfer": (5, 60),     # 5 переводов / 60 сек
    "action":  (30, 60),     # 30 actions / 60 сек
}


async def is_rate_limited(user_id: str, action: str = "message") -> bool:
    """
    Проверяет, превысил ли пользователь лимит для данного действия.
    Возвращает True если лимит превышен (нужно блокировать запрос).
    """
    limit, window = DEFAULT_LIMITS.get(action, (30, 60))
    key = rate_limit_key(user_id, action)
    redis = get_redis()

    count = await redis.incr(key)
    if count == 1:
        # Первый запрос в окне — устанавливаем TTL
        await redis.expire(key, window)

    return count > limit


async def get_remaining(user_id: str, action: str = "message") -> int:
    """Возвращает сколько запросов осталось в текущем окне."""
    limit, _ = DEFAULT_LIMITS.get(action, (30, 60))
    key = rate_limit_key(user_id, action)
    redis = get_redis()
    count = await redis.get(key)
    if not count:
        return limit
    return max(0, limit - int(count))


async def reset_rate_limit(user_id: str, action: str = "message") -> None:
    """Сбрасывает лимит для пользователя (используется в тестах и админке)."""
    key = rate_limit_key(user_id, action)
    redis = get_redis()
    await redis.delete(key)


async def set_custom_limit(user_id: str, action: str, limit: int, window: int) -> None:
    """
    Устанавливает кастомный лимит для конкретного пользователя.
    Используется из админпанели для ужесточения или снятия ограничений.
    """
    # Сохраняем кастомный лимит в Redis
    redis = get_redis()
    await redis.set(f"rl_custom:{action}:{user_id}", f"{limit}:{window}")
