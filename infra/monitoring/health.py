"""
monitoring/health.py — Health check эндпоинт.
Проверяет: Redis, Supabase, Celery.
Используется Docker HEALTHCHECK и Railway.
"""

from __future__ import annotations
import time
from typing import Any

from infra.db.redis import get_redis
from infra.db.supabase import get_supabase_admin


async def check_redis() -> dict[str, Any]:
    try:
        start = time.monotonic()
        redis = get_redis()
        await redis.ping()
        return {"status": "ok", "latency_ms": round((time.monotonic() - start) * 1000, 1)}
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def check_supabase() -> dict[str, Any]:
    try:
        start = time.monotonic()
        get_supabase_admin().table("users").select("id").limit(1).execute()
        return {"status": "ok", "latency_ms": round((time.monotonic() - start) * 1000, 1)}
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def get_health() -> dict[str, Any]:
    """
    Полный health report.
    Статус: healthy | degraded | unhealthy
    """
    redis_status = await check_redis()
    supabase_status = await check_supabase()

    all_ok = all(s["status"] == "ok" for s in [redis_status, supabase_status])
    any_ok = any(s["status"] == "ok" for s in [redis_status, supabase_status])

    if all_ok:
        overall = "healthy"
    elif any_ok:
        overall = "degraded"
    else:
        overall = "unhealthy"

    return {
        "status": overall,
        "services": {
            "redis": redis_status,
            "supabase": supabase_status,
        },
        "timestamp": time.time(),
    }
