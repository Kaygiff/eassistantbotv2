"""
economy/referral.py — Реферальная система.
Генерация ссылок, выдача бонусов, комиссия с рефералов.
"""

from __future__ import annotations
import os
import uuid
import hashlib

from infra.db.supabase import get_supabase_admin
from world.economy.wallet import credit

REFERRAL_BONUS = int(os.getenv("REFERRAL_BONUS", 100))
REFERRAL_COMMISSION = int(os.getenv("REFERRAL_COMMISSION_PERCENT", 10))
BOT_USERNAME = os.getenv("BOT_USERNAME", "envertassisbot")


def generate_ref_code(telegram_id: int) -> str:
    """Генерирует уникальный реферальный код для пользователя."""
    raw = f"{telegram_id}:eassistant:ref"
    return hashlib.md5(raw.encode()).hexdigest()[:10].upper()


async def get_referral_info(user_id: str, telegram_id: int, language: str) -> str:
    """Возвращает реферальную информацию пользователя."""
    ref_code = generate_ref_code(telegram_id)
    ref_link = f"https://t.me/{BOT_USERNAME}?start=ref_{ref_code}"

    # Считаем рефералов
    res = (
        get_supabase_admin().table("referrals")
        .select("id, bonus_paid, total_commission_earned", count="exact")
        .eq("referrer_id", user_id)
        .execute()
    )
    referrals = res.data or []
    total_count = res.count or 0
    total_commission = sum(r.get("total_commission_earned", 0) for r in referrals)

    text = (
        f"👥 *Реферальная программа*\n\n"
        f"🔗 Твоя ссылка:\n`{ref_link}`\n\n"
        f"📊 Статистика:\n"
        f"• Рефералов: *{total_count}*\n"
        f"• Бонус за каждого: *{REFERRAL_BONUS} Ecoins*\n"
        f"• Твоя комиссия: *{REFERRAL_COMMISSION}%* с бонусов реферала\n"
        f"• Заработано комиссий: *{total_commission} Ecoins*\n\n"
        f"💡 Поделись ссылкой — и получай бонусы!"
    )
    return text


async def process_referral(referee_telegram_id: int, ref_code: str) -> None:
    """
    Обрабатывает реферальное приглашение при регистрации нового пользователя.
    Вызывается из auth/identity.py при первом /start с параметром ref_code.
    """
    # Находим реферера по коду
    all_users = get_supabase_admin().table("users").select("id, telegram_id").execute()
    referrer = None
    for user in (all_users.data or []):
        if generate_ref_code(user["telegram_id"]) == ref_code:
            referrer = user
            break

    if not referrer:
        return

    # Находим реферала
    referee = (
        get_supabase_admin().table("users")
        .select("id")
        .eq("telegram_id", referee_telegram_id)
        .maybe_single()
        .execute()
    )
    if not referee.data:
        return

    referee_id = referee.data["id"]
    referrer_id = referrer["id"]

    # Проверяем что реферал ещё не зарегистрирован через эту ссылку
    existing = (
        get_supabase_admin().table("referrals")
        .select("id")
        .eq("referee_id", referee_id)
        .maybe_single()
        .execute()
    )
    if existing.data:
        return

    # Создаём запись
    get_supabase_admin().table("referrals").insert({
        "id": str(uuid.uuid4()),
        "referrer_id": referrer_id,
        "referee_id": referee_id,
        "ref_code": ref_code,
        "bonus_paid": True,
    }).execute()

    # Выдаём бонус рефереру
    await credit(referrer_id, REFERRAL_BONUS, "referral_signup", referee_id)

    # Уведомляем реферера
    from infra.notifications.sender import notify_user
    await notify_user(
        referrer_id,
        f"🎉 По твоей реферальной ссылке зарегистрировался новый пользователь!\n💰 +{REFERRAL_BONUS} Ecoins"
    )
