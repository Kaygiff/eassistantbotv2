"""
auth/identity.py — Идентификация пользователя.
Telegram ID (внешний) + внутренний UUID.
Получение или создание профиля при первом обращении.
"""

from __future__ import annotations
import uuid
from typing import Optional

from db.supabase import supabase_admin
from models.user import User, UserCreate


async def get_user_by_telegram_id(telegram_id: int) -> Optional[User]:
    """Возвращает пользователя по Telegram ID или None если не найден."""
    res = (
        supabase_admin
        .table("users")
        .select("*")
        .eq("telegram_id", telegram_id)
        .maybe_single()
        .execute()
    )
    if res.data:
        return User(**res.data)
    return None


async def get_user_by_uuid(user_id: str) -> Optional[User]:
    """Возвращает пользователя по внутреннему UUID."""
    res = (
        supabase_admin
        .table("users")
        .select("*")
        .eq("id", user_id)
        .maybe_single()
        .execute()
    )
    if res.data:
        return User(**res.data)
    return None


async def create_user(data: UserCreate) -> User:
    """
    Создаёт нового пользователя + кошелёк + запись daily_bonuses.
    Всё в одной транзакции через последовательные вызовы.
    """
    user_id = str(uuid.uuid4())

    # 1. Создать пользователя
    user_res = (
        supabase_admin
        .table("users")
        .insert({
            "id": user_id,
            "telegram_id": data.telegram_id,
            "username": data.username,
            "first_name": data.first_name,
            "language": data.language,
            "assistant_name": data.assistant_name,
        })
        .execute()
    )
    user = User(**user_res.data[0])

    # 2. Создать кошелёк
    supabase_admin.table("ecoin_wallets").insert({
        "user_id": user_id,
        "balance": 0,
    }).execute()

    # 3. Инициализировать daily_bonuses
    supabase_admin.table("daily_bonuses").insert({
        "user_id": user_id,
        "streak_days": 0,
    }).execute()

    return user


async def get_or_create_user(
    telegram_id: int,
    username: Optional[str] = None,
    first_name: Optional[str] = None,
) -> tuple[User, bool]:
    """
    Возвращает (user, is_new).
    is_new=True если пользователь только что создан.
    """
    user = await get_user_by_telegram_id(telegram_id)
    if user:
        return user, False

    # Создаём с временным именем ассистента — онбординг его установит
    new_user = await create_user(UserCreate(
        telegram_id=telegram_id,
        username=username,
        first_name=first_name,
        language="ru",
        assistant_name="Ассистент",
    ))
    return new_user, True


async def update_user_field(user_id: str, **fields) -> User:
    """Обновляет произвольные поля профиля пользователя."""
    res = (
        supabase_admin
        .table("users")
        .update(fields)
        .eq("id", user_id)
        .execute()
    )
    return User(**res.data[0])
