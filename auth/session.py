"""
auth/session.py — Управление сессиями пользователей.
Сессия бессрочная (TTL не применяется по документации).
Хранится в Redis. Персистентные данные — в Supabase.
"""

from __future__ import annotations
import json
from typing import Any, Optional

from db.redis import get_redis, session_key, fsm_key


async def get_session(user_id: str) -> dict[str, Any]:
    """Возвращает текущую сессию пользователя из Redis."""
    redis = get_redis()
    raw = await redis.get(session_key(user_id))
    if raw:
        return json.loads(raw)
    return {}


async def set_session(user_id: str, data: dict[str, Any]) -> None:
    """Сохраняет сессию. TTL не устанавливается (бессрочно)."""
    redis = get_redis()
    await redis.set(session_key(user_id), json.dumps(data, ensure_ascii=False))


async def update_session(user_id: str, **kwargs) -> dict[str, Any]:
    """Обновляет отдельные поля сессии, не затрагивая остальные."""
    session = await get_session(user_id)
    session.update(kwargs)
    await set_session(user_id, session)
    return session


async def clear_session(user_id: str) -> None:
    """Очищает сессию (например при logout или сбросе)."""
    redis = get_redis()
    await redis.delete(session_key(user_id))


# --- FSM (Finite State Machine) ---
# Используется в онбординге и редактировании профиля

async def get_fsm_state(user_id: str) -> Optional[str]:
    """Возвращает текущее FSM-состояние пользователя."""
    redis = get_redis()
    return await redis.get(fsm_key(user_id))


async def set_fsm_state(user_id: str, state: str) -> None:
    """Устанавливает FSM-состояние."""
    redis = get_redis()
    await redis.set(fsm_key(user_id), state)


async def clear_fsm_state(user_id: str) -> None:
    """Сбрасывает FSM-состояние после завершения диалога."""
    redis = get_redis()
    await redis.delete(fsm_key(user_id))


async def get_fsm_data(user_id: str) -> dict[str, Any]:
    """Возвращает временные данные FSM-диалога (например, имя питомца)."""
    redis = get_redis()
    raw = await redis.get(f"fsm_data:{user_id}")
    if raw:
        return json.loads(raw)
    return {}


async def set_fsm_data(user_id: str, data: dict[str, Any]) -> None:
    """Сохраняет временные данные FSM-диалога."""
    redis = get_redis()
    await redis.set(f"fsm_data:{user_id}", json.dumps(data, ensure_ascii=False))


async def clear_fsm_data(user_id: str) -> None:
    redis = get_redis()
    await redis.delete(f"fsm_data:{user_id}")
