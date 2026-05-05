"""
safety/group_moderation.py — Модерация групповых чатов.
Варны, муты, баны, кики, роли — всё на уровне группы.
Все действия логируются в audit_log.
"""

from __future__ import annotations
import uuid
from datetime import datetime, timezone
from typing import Optional

from infra.db.supabase import get_supabase_admin
from api.audit.logger import log_action

# ---------------------------------------------------------------------------
# Иерархия ролей
# ---------------------------------------------------------------------------

ROLE_HIERARCHY = ["user", "vip", "moderator", "admin", "co_owner", "owner"]

ROLE_PROMOTE_LIMIT: dict[str, str] = {
    "owner":     "co_owner",
    "co_owner":  "admin",
    "admin":     "vip",
    "moderator": "vip",
    "vip":       "",
    "user":      "",
}

CAN_MUTE    = {"owner", "co_owner", "admin", "moderator"}
CAN_BAN     = {"owner", "co_owner", "admin"}
CAN_KICK    = {"owner", "co_owner", "admin", "moderator"}
CAN_WARN    = {"owner", "co_owner", "admin", "moderator"}
CAN_PROMOTE = {"owner", "co_owner", "admin", "moderator"}


def role_index(role: str) -> int:
    try:
        return ROLE_HIERARCHY.index(role)
    except ValueError:
        return 0


# ---------------------------------------------------------------------------
# Получение роли
# ---------------------------------------------------------------------------

async def get_group_member_role(group_id: str, user_id: str) -> str:
    res = (
        get_supabase_admin()
        .table("group_members")
        .select("role")
        .eq("group_id", group_id)
        .eq("user_id", user_id)
        .maybe_single()
        .execute()
    )
    return res.data["role"] if res.data else "user"


async def can_moderate(group_id: str, user_id: str) -> bool:
    role = await get_group_member_role(group_id, user_id)
    return role in CAN_WARN


# ---------------------------------------------------------------------------
# Ensure group exists + определение owner через Telegram
# ---------------------------------------------------------------------------

async def ensure_group_exists(chat_id: int, title: str, owner_id: Optional[str] = None) -> str:
    res = (
        get_supabase_admin()
        .table("groups")
        .select("id")
        .eq("chat_id", chat_id)
        .limit(1)
        .execute()
    )
    if res and res.data:
        return res.data[0]["id"]

    group_id = str(uuid.uuid4())
    get_supabase_admin().table("groups").insert({
        "id": group_id,
        "chat_id": chat_id,
        "title": title,
        "owner_id": owner_id,
    }).execute()
    return group_id


async def sync_group_owner(group_id: str, bot, chat_id: int) -> None:
    """Определяет владельца группы через Telegram API и записывает его в БД."""
    try:
        admins = await bot.get_chat_administrators(chat_id)
        for member in admins:
            if member.status == "creator":
                tg_id = member.user.id
                res = (
                    get_supabase_admin()
                    .table("users")
                    .select("id")
                    .eq("telegram_id", tg_id)
                    .maybe_single()
                    .execute()
                )
                if res.data:
                    owner_uuid = res.data["id"]
                    get_supabase_admin().table("groups").update(
                        {"owner_id": owner_uuid}
                    ).eq("id", group_id).execute()
                    await set_member_role(group_id, owner_uuid, "owner")
                break
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Роли
# ---------------------------------------------------------------------------

async def set_member_role(group_id: str, user_id: str, role: str) -> None:
    get_supabase_admin().table("group_members").upsert({
        "group_id": group_id,
        "user_id": user_id,
        "role": role,
    }, on_conflict="group_id,user_id").execute()


async def promote_member(
    group_id: str,
    actor_id: str,
    target_id: str,
    steps: int = 1,
) -> tuple[bool, str, str]:
    """Повышает роль target на steps уровней. Возвращает (success, old_role, new_role)."""
    actor_role = await get_group_member_role(group_id, actor_id)
    target_role = await get_group_member_role(group_id, target_id)

    limit_role = ROLE_PROMOTE_LIMIT.get(actor_role, "")
    if not limit_role:
        return False, target_role, target_role

    limit_idx = role_index(limit_role)
    actor_idx = role_index(actor_role)
    target_idx = role_index(target_role)

    if target_idx >= actor_idx:
        return False, target_role, target_role

    new_idx = min(target_idx + steps, limit_idx)
    if new_idx == target_idx:
        return False, target_role, target_role

    new_role = ROLE_HIERARCHY[new_idx]
    await set_member_role(group_id, target_id, new_role)
    await log_action(
        action="group_promote",
        user_id=actor_id,
        details={"target": target_id, "group_id": group_id,
                 "from": target_role, "to": new_role},
    )
    return True, target_role, new_role


async def demote_member(
    group_id: str,
    actor_id: str,
    target_id: str,
    steps: int = 1,
) -> tuple[bool, str, str]:
    """Понижает роль target на steps уровней. Возвращает (success, old_role, new_role)."""
    actor_role = await get_group_member_role(group_id, actor_id)
    target_role = await get_group_member_role(group_id, target_id)

    actor_idx = role_index(actor_role)
    target_idx = role_index(target_role)

    if target_idx >= actor_idx:
        return False, target_role, target_role

    new_idx = max(target_idx - steps, 0)
    if new_idx == target_idx:
        return False, target_role, target_role

    new_role = ROLE_HIERARCHY[new_idx]
    await set_member_role(group_id, target_id, new_role)
    await log_action(
        action="group_demote",
        user_id=actor_id,
        details={"target": target_id, "group_id": group_id,
                 "from": target_role, "to": new_role},
    )
    return True, target_role, new_role


# ---------------------------------------------------------------------------
# Варны
# ---------------------------------------------------------------------------

async def get_warn_count(group_id: str, user_id: str) -> int:
    res = (
        get_supabase_admin()
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
    group_res = (
        get_supabase_admin()
        .table("groups")
        .select("warn_threshold")
        .eq("id", group_id)
        .maybe_single()
        .execute()
    )
    threshold = group_res.data["warn_threshold"] if group_res.data else 3

    get_supabase_admin().table("group_warns").insert({
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
        details={"target_user_id": user_id, "group_id": group_id,
                 "reason": reason, "warn_count": count, "threshold": threshold},
    )
    return count, threshold


async def unwarn_user(group_id: str, user_id: str) -> int:
    """Снимает последний варн. Возвращает оставшееся количество."""
    res = (
        get_supabase_admin()
        .table("group_warns")
        .select("id, created_at")
        .eq("group_id", group_id)
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    if res.data:
        get_supabase_admin().table("group_warns").delete().eq(
            "id", res.data[0]["id"]
        ).execute()
    return await get_warn_count(group_id, user_id)


async def clear_warns(group_id: str, user_id: str) -> None:
    get_supabase_admin().table("group_warns").delete().eq(
        "group_id", group_id
    ).eq("user_id", user_id).execute()


# ---------------------------------------------------------------------------
# Групповой бан
# ---------------------------------------------------------------------------

async def is_group_banned(group_id: str, user_id: str) -> bool:
    res = (
        get_supabase_admin()
        .table("group_bans")
        .select("id, ban_until")
        .eq("group_id", group_id)
        .eq("user_id", user_id)
        .maybe_single()
        .execute()
    )
    if not res.data:
        return False
    ban_until = res.data.get("ban_until")
    if ban_until and datetime.now(timezone.utc) > datetime.fromisoformat(ban_until):
        await unban_from_group(group_id, user_id)
        return False
    return True


async def ban_from_group(
    group_id: str,
    user_id: str,
    banned_by: Optional[str],
    reason: Optional[str] = None,
    ban_until: Optional[datetime] = None,
) -> None:
    get_supabase_admin().table("group_bans").upsert({
        "group_id": group_id,
        "user_id": user_id,
        "banned_by": banned_by,
        "reason": reason,
        "ban_until": ban_until.isoformat() if ban_until else None,
    }, on_conflict="group_id,user_id").execute()

    await log_action(
        action="group_ban",
        user_id=banned_by,
        details={"target": user_id, "group_id": group_id,
                 "reason": reason,
                 "until": ban_until.isoformat() if ban_until else "permanent"},
    )


async def unban_from_group(group_id: str, user_id: str) -> None:
    get_supabase_admin().table("group_bans").delete().eq(
        "group_id", group_id
    ).eq("user_id", user_id).execute()


# ---------------------------------------------------------------------------
# Групповой мут
# ---------------------------------------------------------------------------

async def is_group_muted(group_id: str, user_id: str) -> bool:
    res = (
        get_supabase_admin()
        .table("group_mutes")
        .select("id, mute_until")
        .eq("group_id", group_id)
        .eq("user_id", user_id)
        .maybe_single()
        .execute()
    )
    if not res.data:
        return False
    if datetime.now(timezone.utc) > datetime.fromisoformat(res.data["mute_until"]):
        await unmute_in_group(group_id, user_id)
        return False
    return True


async def mute_in_group(
    group_id: str,
    user_id: str,
    muted_by: Optional[str],
    mute_until: datetime,
    reason: Optional[str] = None,
) -> None:
    get_supabase_admin().table("group_mutes").upsert({
        "group_id": group_id,
        "user_id": user_id,
        "muted_by": muted_by,
        "reason": reason,
        "mute_until": mute_until.isoformat(),
    }, on_conflict="group_id,user_id").execute()

    await log_action(
        action="group_mute",
        user_id=muted_by,
        details={"target": user_id, "group_id": group_id,
                 "reason": reason, "until": mute_until.isoformat()},
    )


async def unmute_in_group(group_id: str, user_id: str) -> None:
    get_supabase_admin().table("group_mutes").delete().eq(
        "group_id", group_id
    ).eq("user_id", user_id).execute()
