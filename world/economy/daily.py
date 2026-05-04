"""
economy/daily.py — Ежедневный бонус и стрик.
Базовый бонус + стрик-множитель. Сброс через Celery Beat.
"""

from __future__ import annotations
import os
from datetime import datetime, timezone, timedelta

from infra.db.supabase import supabase_admin
from world.economy.wallet import credit
from core.i18n import t

BASE_BONUS = int(os.getenv("DAILY_BONUS_BASE", 200))
MAX_STREAK_MULTIPLIER = 3.0  # максимум x3 при стрике >= 30 дней


def _calc_bonus(streak: int) -> int:
    """Считает бонус с учётом стрика."""
    multiplier = min(1.0 + streak * 0.1, MAX_STREAK_MULTIPLIER)
    return int(BASE_BONUS * multiplier)


async def claim_daily_bonus(user_id: str, language: str = "ru") -> str:
    """
    Выдаёт ежедневный бонус пользователю.
    Возвращает форматированное сообщение.
    """
    now = datetime.now(timezone.utc)

    res = (
        supabase_admin.table("daily_bonuses")
        .select("*")
        .eq("user_id", user_id)
        .maybe_single()
        .execute()
    )
    record = res.data

    if not record:
        # Первый раз — создаём запись
        supabase_admin.table("daily_bonuses").insert({
            "user_id": user_id,
            "streak_days": 0,
        }).execute()
        record = {"streak_days": 0, "last_bonus_at": None}

    last_bonus_at = record.get("last_bonus_at")
    streak = record.get("streak_days", 0)

    if last_bonus_at:
        last_dt = datetime.fromisoformat(last_bonus_at)
        if last_dt.tzinfo is None:
            last_dt = last_dt.replace(tzinfo=timezone.utc)

        # Уже получили сегодня
        if now.date() == last_dt.date():
            return t(language, "economy.already_claimed")

        # Пропустили день — сброс стрика
        if now.date() > last_dt.date() + timedelta(days=1):
            streak = 0
            supabase_admin.table("daily_bonuses").update({
                "streak_days": 0
            }).eq("user_id", user_id).execute()

    new_streak = streak + 1
    amount = _calc_bonus(new_streak)

    # Обновляем запись
    supabase_admin.table("daily_bonuses").update({
        "streak_days": new_streak,
        "last_bonus_at": now.isoformat(),
        "total_bonuses_earned": supabase_admin.table("daily_bonuses")
            .select("total_bonuses_earned")
            .eq("user_id", user_id)
            .maybe_single()
            .execute().data.get("total_bonuses_earned", 0) + amount,
    }).eq("user_id", user_id).execute()

    # Зачисляем бонус
    await credit(user_id, amount, "daily_bonus")

    return t(language, "economy.daily_bonus", amount=amount, streak=new_streak)
