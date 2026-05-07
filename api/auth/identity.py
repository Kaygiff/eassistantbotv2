"""
auth/identity.py — Идентификация пользователя.
Telegram ID (внешний) + внутренний UUID.
Получение или создание профиля при первом обращении.
При каждом входе синхронизирует username/имя/premium из Telegram.
"""

from __future__ import annotations
import uuid
from typing import Optional

from infra.db.supabase import get_supabase_admin
from core.models.user import User, UserCreate


async def get_user_by_telegram_id(telegram_id: int) -> Optional[User]:
    """Возвращает пользователя по Telegram ID или None если не найден."""
    res = (
        get_supabase_admin()
        .table("users")
        .select("*")
        .eq("telegram_id", telegram_id)
        .limit(1)
        .execute()
    )
    if res.data:
        return User(**res.data[0])
    return None


async def get_user_by_uuid(user_id: str) -> Optional[User]:
    """Возвращает пользователя по внутреннему UUID."""
    res = (
        get_supabase_admin()
        .table("users")
        .select("*")
        .eq("id", user_id)
        .limit(1)
        .execute()
    )
    if res.data:
        return User(**res.data[0])
    return None


async def create_user(data: UserCreate) -> User:
    """
    Создаёт нового пользователя + кошелёк + запись daily_bonuses.
    """
    user_id = str(uuid.uuid4())

    # 1. Создать пользователя
    user_res = (
        get_supabase_admin()
        .table("users")
        .insert({
            "id": user_id,
            "telegram_id": data.telegram_id,
            "username": data.username,
            "first_name": data.first_name,
            "last_name": data.last_name,
            "language": data.language,
            "locale": data.locale,
            "is_premium": data.is_premium,
            "assistant_name": data.assistant_name,
        })
        .execute()
    )
    user = User(**user_res.data[0])

    # 2. Создать кошелёк
    get_supabase_admin().table("ecoin_wallets").insert({
        "user_id": user_id,
        "balance": 0,
    }).execute()

    # 3. Инициализировать daily_bonuses
    get_supabase_admin().table("daily_bonuses").insert({
        "user_id": user_id,
        "streak_days": 0,
    }).execute()

    return user


async def sync_user_telegram_data(
    user: User,
    username: Optional[str],
    first_name: Optional[str],
    last_name: Optional[str],
    is_premium: bool,
    locale: Optional[str],
) -> User:
    """
    Обновляет username/имя/premium если они изменились в Telegram.
    Также обновляет last_seen_at и инкрементирует messages_count.
    Возвращает обновлённого пользователя.
    """
    updates: dict = {
        "last_seen_at": "now()",
        "messages_count": user.messages_count + 1,
    }

    if user.username != username:
        updates["username"] = username
    if user.first_name != first_name:
        updates["first_name"] = first_name
    if user.last_name != last_name:
        updates["last_name"] = last_name
    if user.is_premium != is_premium:
        updates["is_premium"] = is_premium
    if locale and user.locale != locale:
        updates["locale"] = locale

    res = (
        get_supabase_admin()
        .table("users")
        .update(updates)
        .eq("id", str(user.id))
        .execute()
    )
    return User(**res.data[0])


async def get_or_create_user(
    telegram_id: int,
    username: Optional[str] = None,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    is_premium: bool = False,
    locale: Optional[str] = None,
) -> tuple[User, bool]:
    """
    Возвращает (user, is_new).
    is_new=True если пользователь только что создан.
    При каждом вызове синхронизирует данные из Telegram.
    """
    user = await get_user_by_telegram_id(telegram_id)

    if user:
        # Синхронизируем Telegram-данные при каждом входе
        user = await sync_user_telegram_data(
            user=user,
            username=username,
            first_name=first_name,
            last_name=last_name,
            is_premium=is_premium,
            locale=locale,
        )
        return user, False

    # Создаём с временным именем ассистента — онбординг его установит
    new_user = await create_user(UserCreate(
        telegram_id=telegram_id,
        username=username,
        first_name=first_name,
        last_name=last_name,
        language="ru",
        locale=locale,
        is_premium=is_premium,
        assistant_name="Ассистент",
    ))
    return new_user, True


async def update_user_field(user_id: str, **fields) -> User:
    """Обновляет произвольные поля профиля пользователя."""
    res = (
        get_supabase_admin()
        .table("users")
        .update(fields)
        .eq("id", user_id)
        .execute()
    )
    return User(**res.data[0])

