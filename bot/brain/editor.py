"""
brain/editor.py — Brain Editor API.
Позволяет редактировать ключевые слова классификатора через EAdmin
без перезапуска сервиса. Правила хранятся в Supabase,
загружаются в Redis-кэш и применяются в classifier.py.
"""

from __future__ import annotations
import json
import logging
from typing import Any

from infra.db.supabase import get_supabase_admin
from infra.db.redis import get_redis

logger = logging.getLogger(__name__)

BRAIN_RULES_CACHE_KEY = "brain:rules"
BRAIN_RULES_CACHE_TTL = 300  # 5 минут


async def get_all_rules() -> list[dict[str, Any]]:
    """
    Возвращает все правила классификатора из Supabase.
    Используется Brain Editor в EAdmin для отображения.
    """
    res = (
        supabase_admin
        .table("brain_rules")
        .select("*")
        .order("intent")
        .execute()
    )
    return res.data or []


async def get_rules_for_intent(intent: str) -> list[str]:
    """Возвращает список ключевых слов для конкретного интента."""
    res = (
        supabase_admin
        .table("brain_rules")
        .select("keywords")
        .eq("intent", intent)
        .maybe_single()
        .execute()
    )
    if res.data:
        return res.data.get("keywords", [])
    return []


async def update_rule(intent: str, keywords: list[str]) -> dict[str, Any]:
    """
    Обновляет ключевые слова для интента.
    После обновления сбрасывает кэш — новые правила применятся сразу.
    """
    res = (
        supabase_admin
        .table("brain_rules")
        .upsert({
            "intent": intent,
            "keywords": keywords,
        })
        .execute()
    )

    # Сброс кэша
    await invalidate_rules_cache()

    logger.info(f"[BrainEditor] Updated rules for intent={intent}: {len(keywords)} keywords")
    return res.data[0] if res.data else {}


async def delete_rule(intent: str) -> None:
    """Удаляет правило для интента (откат к дефолтным ключевым словам)."""
    get_supabase_admin().table("brain_rules").delete().eq("intent", intent).execute()
    await invalidate_rules_cache()


async def get_cached_rules() -> dict[str, list[str]] | None:
    """
    Возвращает правила из Redis-кэша.
    None если кэш пустой или устарел.
    """
    redis = get_redis()
    raw = await redis.get(BRAIN_RULES_CACHE_KEY)
    if raw:
        return json.loads(raw)
    return None


async def cache_rules(rules: dict[str, list[str]]) -> None:
    """Сохраняет правила в Redis-кэш."""
    redis = get_redis()
    await redis.setex(
        BRAIN_RULES_CACHE_KEY,
        BRAIN_RULES_CACHE_TTL,
        json.dumps(rules, ensure_ascii=False),
    )


async def invalidate_rules_cache() -> None:
    """Принудительно сбрасывает кэш правил."""
    redis = get_redis()
    await redis.delete(BRAIN_RULES_CACHE_KEY)


async def load_rules_into_classifier() -> int:
    """
    Загружает кастомные правила из Supabase в classifier.py.
    Вызывается при старте приложения и после обновлений через EAdmin.
    Возвращает количество загруженных правил.
    """
    from bot.brain.classifier import PATTERN_MAP
    from bot.brain.intent import Intent

    # Сначала проверяем кэш
    cached = await get_cached_rules()
    if cached:
        rules_data = cached
    else:
        # Загружаем из Supabase
        all_rules = await get_all_rules()
        rules_data = {r["intent"]: r["keywords"] for r in all_rules}
        await cache_rules(rules_data)

    if not rules_data:
        return 0

    # Применяем кастомные правила — добавляем в начало PATTERN_MAP
    # (более высокий приоритет чем дефолтные)
    injected = 0
    for intent_str, keywords in rules_data.items():
        try:
            intent = Intent(intent_str)
            # Проверяем нет ли уже такого правила
            existing_intents = [i for _, i in PATTERN_MAP]
            if intent not in existing_intents:
                PATTERN_MAP.insert(0, (keywords, intent))
            else:
                # Обновляем существующее
                for idx, (kws, i) in enumerate(PATTERN_MAP):
                    if i == intent:
                        PATTERN_MAP[idx] = (keywords, intent)
                        break
            injected += 1
        except ValueError:
            logger.warning(f"[BrainEditor] Unknown intent: {intent_str}")

    logger.info(f"[BrainEditor] Loaded {injected} custom rules into classifier")
    return injected


async def get_editor_stats() -> dict[str, Any]:
    """
    Возвращает статистику Brain Editor для EAdmin дашборда.
    """
    from bot.brain.router import get_registered_intents
    from bot.brain.classifier import PATTERN_MAP

    return {
        "total_intents": len(get_registered_intents()),
        "total_keyword_rules": len(PATTERN_MAP),
        "custom_rules_count": len(await get_all_rules()),
        "cache_active": (await get_cached_rules()) is not None,
    }
