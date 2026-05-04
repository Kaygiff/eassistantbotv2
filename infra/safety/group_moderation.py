"""
safety/group_moderation.py — Модерация групповых чатов.
Варны, муты, кики, автобан при достижении порога.
Все действия логируются в audit_log.
"""

from __future__ import annotations
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from infra.db.supabase import supabase_admin
from api.audit.logger import log_action


async def get_warn_count(group_id: str, user_id: str) -> int:
    """Возвращает количество активных предупреждений пользователя в группе."""
    res = (
        supabase_admin
        .table("group_warns")
        .select("id", count="exact")
        .eq("group_id", group_id)
        .eq("user_id", user_id)
        .execute()
    )
    return res.count or 0


async def warn_user(
    group_id: str,
    user_id: str,
    issued_by: Optional[str],
    reason: Optional[str] = None,
) -> tuple[int, int]:
    """
    Выдаёт предупреждение пользователю.
    Возвращает (текущее_количество_варнов, порог_автобана).
    """
    # Получаем порог из настроек группы
    group_res = (
        supabase_admin
        .table("groups")
        .select("warn_threshold")
        .eq("id", group_id)
        .maybe_single()
        .execute()
    )
    threshold = group_res.data["warn_threshold"] if group_res.data else 3

    # Добавляем варн
    supabase_admin.table("group_warns").insert({
        "id": str(uuid.uuid4()),
        "group_id": group_id,
        "user_id": user_id,
        "issued_by": issued_by,
        "reason": reason,
    }).execute()

    count = await get_warn_count(group_id, user_id)

    await log_action(
        action="group_warn",
        user_id=issued_by,
        details={
            "target_user_id": user_id,
            "group_id": group_id,
            "reason": reason,
            "warn_count": count,
            "threshold": threshold,
        },
    )

    return count, threshold


async def clear_warns(group_id: str, user_id: str) -> None:
    """Удаляет все предупреждения пользователя в группе."""
    supabase_admin.table("group_warns").delete().eq("group_id", group_id).eq("user_id", user_id).execute()


async def get_group_member_role(group_id: str, user_id: str) -> Optional[str]:
    """Возвращает роль пользователя в группе или None если не в группе."""
    res = (
        supabase_admin
        .table("group_members")
        .select("role")
        .eq("group_id", group_id)
        .eq("user_id", user_id)
        .maybe_single()
        .execute()
    )
    return res.data["role"] if res.data else None


async def can_moderate(group_id: str, user_id: str) -> bool:
    """
    Проверяет, имеет ли пользователь права модератора в группе.
    Роли: owner, co_owner, admin, moderator.
    """
    role = await get_group_member_role(group_id, user_id)
    return role in ("owner", "co_owner", "admin", "moderator")


async def set_member_role(group_id: str, user_id: str, role: str) -> None:
    """Устанавливает роль участника группы."""
    supabase_admin.table("group_members").upsert({
        "group_id": group_id,
        "user_id": user_id,
        "role": role,
    }).execute()


async def ensure_group_exists(chat_id: int, title: str, owner_id: Optional[str] = None) -> str:
    """
    Создаёт запись группы если она ещё не существует.
    Возвращает UUID группы.
    """
    res = (
        supabase_admin
        .table("groups")
        .select("id")
        .eq("chat_id", chat_id)
        .maybe_single()
        .execute()
    )
    if res.data:
        return res.data["id"]

    group_id = str(uuid.uuid4())
    supabase_admin.table("groups").insert({
        "id": group_id,
        "chat_id": chat_id,
        "title": title,
        "owner_id": owner_id,
    }).execute()
    return group_id
