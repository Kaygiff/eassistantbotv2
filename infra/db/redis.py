"""
Redis клиент.
Используется для: сессий, кэша, FSM-состояний, rate limit, feature flags, Celery broker.
"""

import os
from functools import lru_cache
from typing import Optional
import redis.asyncio as aioredis
import redis as syncredis


REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")


@lru_cache()
def get_redis_pool() -> aioredis.ConnectionPool:
    return aioredis.ConnectionPool.from_url(
        REDIS_URL,
        encoding="utf-8",
        decode_responses=True,
        max_connections=50,
    )


def get_redis() -> aioredis.Redis:
    """Async Redis клиент — для использования в FastAPI и сервисах."""
    return aioredis.Redis(connection_pool=get_redis_pool())


def get_sync_redis() -> syncredis.Redis:
    """Sync Redis клиент — для Celery tasks."""
    return syncredis.from_url(REDIS_URL, encoding="utf-8", decode_responses=True)


# --- Key builders ---
# Единое место для формирования Redis-ключей, чтобы избежать дублей

def session_key(user_id: str) -> str:
    return f"session:{user_id}"

def fsm_key(user_id: str) -> str:
    return f"fsm:{user_id}"

def rate_limit_key(user_id: str, action: str) -> str:
    return f"rl:{action}:{user_id}"

def chat_history_key(user_id: str) -> str:
    return f"chat:history:{user_id}"

def feature_flag_key(flag_name: str) -> str:
    return f"ff:{flag_name}"

def weather_cache_key(city: str, lang: str) -> str:
    return f"weather:{lang}:{city.lower()}"

def encyclopedia_cache_key(query: str, lang: str) -> str:
    return f"enc:{lang}:{query[:50].lower()}"

def pet_decay_lock_key(user_id: str) -> str:
    return f"pet:decay_lock:{user_id}"

def cooldown_key(initiator_id: str, target_id: str, action_type: str) -> str:
    return f"cooldown:{action_type}:{initiator_id}:{target_id}"
