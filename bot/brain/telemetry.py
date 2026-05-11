"""
bot/brain/telemetry.py — Телеметрия классификатора интентов.

Пишет в Redis sorted set и список событий:
  - brain:telemetry:intents  — ZINCRBY: счётчик срабатываний по intent
  - brain:telemetry:providers — ZINCRBY: счётчик вызовов Brain AI по провайдеру
  - brain:telemetry:latency  — LPUSH: список latency (мс) последних 500 вызовов

Данные читает EAdmin /brain/stats (brain_editor.py → editor.py get_editor_stats).
Не ломает основной поток при любой ошибке Redis.
"""

from __future__ import annotations
import logging
import time
from contextlib import asynccontextmanager
from typing import AsyncIterator

from infra.db.redis import get_redis
from bot.brain.intent import Intent

logger = logging.getLogger(__name__)

_KEY_INTENTS   = "brain:telemetry:intents"
_KEY_PROVIDERS = "brain:telemetry:providers"
_KEY_LATENCY   = "brain:telemetry:latency"
_LATENCY_MAX   = 500       # хранить не более N последних значений
_TTL_STATS     = 86400 * 7  # 7 дней


async def record_intent(intent: Intent, source: str = "pattern") -> None:
    """
    Записывает факт классификации интента.

    source: "pattern" | "brain_ai" | "cache"
    """
    try:
        redis = get_redis()
        key = f"{_KEY_INTENTS}:{source}"
        await redis.zincrby(key, 1, intent.value)
        await redis.expire(key, _TTL_STATS)
    except Exception as e:
        logger.debug(f"[Telemetry] record_intent failed: {e}")


async def record_provider(provider_name: str) -> None:
    """Записывает использование конкретного AI-провайдера Brain AI."""
    try:
        redis = get_redis()
        await redis.zincrby(_KEY_PROVIDERS, 1, provider_name)
        await redis.expire(_KEY_PROVIDERS, _TTL_STATS)
    except Exception as e:
        logger.debug(f"[Telemetry] record_provider failed: {e}")


async def record_latency_ms(ms: float) -> None:
    """Записывает latency вызова Brain AI (в мс), держит последние 500."""
    try:
        redis = get_redis()
        await redis.lpush(_KEY_LATENCY, round(ms, 1))
        await redis.ltrim(_KEY_LATENCY, 0, _LATENCY_MAX - 1)
        await redis.expire(_KEY_LATENCY, _TTL_STATS)
    except Exception as e:
        logger.debug(f"[Telemetry] record_latency failed: {e}")


@asynccontextmanager
async def measure_brain_ai(provider_name: str = "") -> AsyncIterator[None]:
    """
    Контекстный менеджер: замеряет latency и пишет телеметрию.

    Использование:
        async with measure_brain_ai(provider_name):
            result = await hub.chat(...)
    """
    start = time.monotonic()
    try:
        yield
    finally:
        elapsed_ms = (time.monotonic() - start) * 1000
        await record_latency_ms(elapsed_ms)
        if provider_name:
            await record_provider(provider_name)


async def get_telemetry_summary() -> dict:
    """
    Возвращает сводку телеметрии для EAdmin /brain/stats.
    """
    try:
        redis = get_redis()

        async def top_zset(key: str, n: int = 10) -> list[dict]:
            raw = await redis.zrevrangebyscore(key, "+inf", "-inf", withscores=True, start=0, num=n)
            return [{"name": name, "count": int(score)} for name, score in raw]

        async def avg_latency() -> float | None:
            raw = await redis.lrange(_KEY_LATENCY, 0, -1)
            if not raw:
                return None
            vals = [float(v) for v in raw]
            return round(sum(vals) / len(vals), 1)

        return {
            "top_intents_pattern": await top_zset(f"{_KEY_INTENTS}:pattern"),
            "top_intents_brain_ai": await top_zset(f"{_KEY_INTENTS}:brain_ai"),
            "top_intents_cache": await top_zset(f"{_KEY_INTENTS}:cache"),
            "top_providers": await top_zset(_KEY_PROVIDERS),
            "avg_brain_ai_latency_ms": await avg_latency(),
        }
    except Exception as e:
        logger.warning(f"[Telemetry] get_summary failed: {e}")
        return {}
