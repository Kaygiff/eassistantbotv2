"""
virtual_world/blacklist/service.py — Чёрный список пользователей.
"""

from __future__ import annotations
import uuid
from db.supabase import supabase_admin


async def add_to_blacklist(blocker_id: str, blocked_username: str, language: str) -> str:
    res = supabase_admin.table("users").select("id, first_name").eq("username", blocked_username).maybe_single().execute()
    if not res.data:
        return "🔍 Пользователь не найден."

    blocked_id = res.data["id"]
    if blocked_id == blocker_id:
        return "🤔 Нельзя заблокировать самого себя."

    supabase_admin.table("blacklist").upsert({
        "id": str(uuid.uuid4()),
        "blocker_id": blocker_id,
        "blocked_id": blocked_id,
    }).execute()

    name = res.data.get("first_name") or f"@{blocked_username}"
    return f"🚫 *{name}* добавлен(а) в чёрный список."


async def remove_from_blacklist(blocker_id: str, blocked_username: str, language: str) -> str:
    res = supabase_admin.table("users").select("id, first_name").eq("username", blocked_username).maybe_single().execute()
    if not res.data:
        return "🔍 Пользователь не найден."

    blocked_id = res.data["id"]
    supabase_admin.table("blacklist").delete().eq("blocker_id", blocker_id).eq("blocked_id", blocked_id).execute()

    name = res.data.get("first_name") or f"@{blocked_username}"
    return f"✅ *{name}* удалён(а) из чёрного списка."


async def is_blocked(blocker_id: str, blocked_id: str) -> bool:
    res = supabase_admin.table("blacklist").select("id").eq("blocker_id", blocker_id).eq("blocked_id", blocked_id).maybe_single().execute()
    return bool(res.data)
