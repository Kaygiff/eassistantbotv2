"""
economy/leaderboard.py — Таблица лидеров по балансу Ecoins.
Используется из EAdmin и команды /top в боте.
Кэш в Redis на 10 минут.
"""

from __future__ import annotations
import json
import logging

from infra.db.supabase import supabase_admin
from infra.db.redis import get_redis

logger = logging.getLogger(__name__)

CACHE_KEY = "economy:leaderboard"
CACHE_TTL = 600  # 10 минут


async def get_top_balances(limit: int = 10, language: str = "ru") -> list[dict]:
    """
    Возвращает топ пользователей по балансу.
    Формат: [{"rank": 1, "name": "...", "balance": 1000}, ...]
    """
    redis = get_redis()

    cached = await redis.get(CACHE_KEY)
    if cached:
        return json.loads(cached)[:limit]

    res = (
        supabase_admin
        .table("ecoin_wallets")
        .select("balance, users(first_name, username)")
        .order("balance", desc=True)
        .limit(50)
        .execute()
    )

    leaderboard = []
    for i, row in enumerate(res.data or [], 1):
        user = row.get("users") or {}
        name = user.get("first_name") or f"@{user.get('username', '???')}"
        leaderboard.append({
            "rank": i,
            "name": name,
            "balance": row["balance"],
        })

    await redis.setex(CACHE_KEY, CACHE_TTL, json.dumps(leaderboard, ensure_ascii=False))
    return leaderboard[:limit]


async def get_leaderboard_text(limit: int = 10, language: str = "ru") -> str:
    """Возвращает форматированный текст таблицы лидеров."""
    top = await get_top_balances(limit, language)

    if not top:
        return "📊 Таблица лидеров пуста."

    medals = {1: "🥇", 2: "🥈", 3: "🥉"}
    lines = ["💰 *Топ по Ecoins:*\n"]

    for entry in top:
        rank = entry["rank"]
        icon = medals.get(rank, f"{rank}.")
        lines.append(f"{icon} {entry['name']} — *{entry['balance']:,} Ecoins*")

    return "\n".join(lines)


async def get_user_rank(user_id: str) -> int | None:
    """Возвращает позицию пользователя в таблице лидеров."""
    top = await get_top_balances(limit=50)
    for entry in top:
        if entry.get("user_id") == user_id:
            return entry["rank"]
    return None


async def invalidate_leaderboard_cache() -> None:
    """Сбрасывает кэш таблицы лидеров (после крупных транзакций)."""
    redis = get_redis()
    await redis.delete(CACHE_KEY)
