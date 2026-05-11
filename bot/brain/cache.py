"""
bot/brain/cache.py — Redis-кэш для классификатора интентов.

Логика:
  - Ключ: нормализованный текст запроса (нижний регистр, strip)
  - TTL: 5 минут (INTENT_CACHE_TTL)
  - Хранит: строку значения Intent
  - При любой ошибке Redis — тихий fallback (не ломает основной поток)

Используется в classifier.classify() перед Brain AI:
  1. Попали в кэш → возвращаем Intent сразу, без вызова модели
  2. Промах → Brain AI → кладём результат в кэш
"""

from __future__ import annotations
import hashlib
import logging
from typing import Optional

from infra.db.redis import get_redis
from bot.brain.intent import Intent

logger = logging.getLogger(__name__)

INTENT_CACHE_TTL = 300          # 5 минут
INTENT_CACHE_PREFIX = "brain:intent:"
# Не кэшируем эти интенты — они зависят от контекста/FSM
_SKIP_CACHE = {Intent.UNKNOWN, Intent.CLARIFICATION, Intent.AI_CHAT}


def _cache_key(text: str) -> str:
    """Стабильный ключ: SHA256 первых 200 символов нормализованного текста."""
    normalized = text.strip().lower()[:200]
    digest = hashlib.sha256(normalized.encode()).hexdigest()[:16]
    return f"{INTENT_CACHE_PREFIX}{digest}"


async def get_cached_intent(text: str) -> Optional[Intent]:
    """
    Возвращает закэшированный Intent или None при промахе / ошибке.
    """
    try:
        redis = get_redis()
        raw = await redis.get(_cache_key(text))
        if raw:
            intent = Intent(raw)
            logger.debug(f"[IntentCache] HIT '{text[:40]}' → {intent.value}")
            return intent
    except Exception as e:
        logger.debug(f"[IntentCache] get failed: {e}")
    return None


async def set_cached_intent(text: str, intent: Intent) -> None:
    """
    Кладёт Intent в кэш. Пропускает нестабильные интенты (_SKIP_CACHE).
    """
    if intent in _SKIP_CACHE:
        return
    try:
        redis = get_redis()
        await redis.setex(_cache_key(text), INTENT_CACHE_TTL, intent.value)
        logger.debug(f"[IntentCache] SET '{text[:40]}' → {intent.value}")
    except Exception as e:
        logger.debug(f"[IntentCache] set failed: {e}")


async def invalidate_intent_cache() -> int:
    """
    Сбрасывает весь intent-кэш (используется после reload правил).
    Возвращает количество удалённых ключей.
    """
    try:
        redis = get_redis()
        keys = await redis.keys(f"{INTENT_CACHE_PREFIX}*")
        if keys:
            await redis.delete(*keys)
            logger.info(f"[IntentCache] Invalidated {len(keys)} keys")
            return len(keys)
    except Exception as e:
        logger.warning(f"[IntentCache] invalidate failed: {e}")
    return 0
