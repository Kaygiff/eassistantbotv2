"""
safety/user_ban.py — Проверка блокировки пользователя.
Safety Layer проверяет бан перед передачей запроса в Brain.
"""

from __future__ import annotations
from datetime import datetime, timezone
from typing import Optional

from db.supabase import supabase_admin
from models.user import User


async def is_banned(user: User) -> bool:
    """
    Проверяет заблокирован ли пользователь.
    Учитывает временные баны (ban_until) и постоянные (ban_until=NULL при is_banned=True).
    """
    if not user.is_banned:
        return False

    # Временный бан — проверяем истёк ли
    if user.ban_until:
        if datetime.now(timezone.utc) > user.ban_until:
            # Бан истёк — снимаем автоматически
            await lift_ban(str(user.id))
            return False
        return True

    # Постоянный бан
    return True


async def ban_user(
    user_id: str,
    reason: Optional[str] = None,
    ban_until: Optional[datetime] = None,
    banned_by: Optional[str] = None,
) -> None:
    """
    Блокирует пользователя.
    ban_until=None означает постоянный бан.
    """
    from audit.logger import log_ban

    update_data: dict = {"is_banned": True, "ban_reason": reason}
    if ban_until:
        update_data["ban_until"] = ban_until.isoformat()

    supabase_admin.table("users").update(update_data).eq("id", user_id).execute()

    await log_ban(
        user_id=user_id,
        banned_by=banned_by,
        reason=reason,
        ban_until=ban_until.isoformat() if ban_until else None,
    )


async def lift_ban(user_id: str) -> None:
    """Снимает блокировку с пользователя."""
    supabase_admin.table("users").update({
        "is_banned": False,
        "ban_until": None,
        "ban_reason": None,
    }).eq("id", user_id).execute()
