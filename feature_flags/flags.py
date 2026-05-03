"""
feature_flags/flags.py — Feature Flags и управление функциональностью.
Конфигурация хранится в Supabase, кэш в Redis.
Применяется без перезапуска сервисов.
"""

from __future__ import annotations
import json
import logging
from typing import Any, Optional

from db.redis import get_redis, feature_flag_key
from db.supabase import supabase_admin

logger = logging.getLogger(__name__)

FLAG_CACHE_TTL = 60  # секунд — как долго кэшировать флаг в Redis


async def get_flag(flag_name: str, default: bool = True) -> bool:
    """
    Возвращает значение feature flag.
    Сначала проверяет Redis-кэш, потом Supabase.
    """
    redis = get_redis()
    key = feature_flag_key(flag_name)

    # 1. Проверяем кэш
    cached = await redis.get(key)
    if cached is not None:
        return cached == "1"

    # 2. Загружаем из Supabase
    try:
        res = (
            supabase_admin
            .table("feature_flags")
            .select("enabled")
            .eq("name", flag_name)
            .maybe_single()
            .execute()
        )
        if res.data:
            value = res.data["enabled"]
            await redis.setex(key, FLAG_CACHE_TTL, "1" if value else "0")
            return value
    except Exception as e:
        logger.warning(f"Failed to load feature flag '{flag_name}': {e}")

    # 3. Дефолт
    return default


async def get_user_flag(flag_name: str, user_id: str, default: bool = True) -> bool:
    """
    Возвращает значение флага для конкретного пользователя.
    Используется для A/B-тестов и персональных rollout'ов.
    """
    redis = get_redis()
    key = f"ff:user:{user_id}:{flag_name}"

    cached = await redis.get(key)
    if cached is not None:
        return cached == "1"

    try:
        res = (
            supabase_admin
            .table("feature_flag_users")
            .select("enabled")
            .eq("flag_name", flag_name)
            .eq("user_id", user_id)
            .maybe_single()
            .execute()
        )
        if res.data:
            value = res.data["enabled"]
            await redis.setex(key, FLAG_CACHE_TTL, "1" if value else "0")
            return value
    except Exception:
        pass

    # Fallback на глобальный флаг
    return await get_flag(flag_name, default)


async def set_flag(flag_name: str, enabled: bool) -> None:
    """
    Устанавливает значение флага в Supabase и сбрасывает кэш.
    Вызывается из EAdmin.
    """
    supabase_admin.table("feature_flags").upsert({
        "name": flag_name,
        "enabled": enabled,
    }).execute()

    # Сбрасываем кэш — следующий запрос загрузит из Supabase
    redis = get_redis()
    await redis.delete(feature_flag_key(flag_name))


async def invalidate_flag_cache(flag_name: str) -> None:
    """Принудительно сбрасывает кэш конкретного флага."""
    redis = get_redis()
    await redis.delete(feature_flag_key(flag_name))
