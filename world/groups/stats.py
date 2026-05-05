"""
groups/stats.py — Статистика группы.
"""

from __future__ import annotations
from infra.db.supabase import get_supabase_admin


async def get_group_stats(group_id: str, language: str) -> str:
    if not group_id:
        return "❌ Группа не найдена."

    members_res = get_supabase_admin().table("group_members").select("id", count="exact").eq("group_id", group_id).execute()
    warns_res = get_supabase_admin().table("group_warns").select("id", count="exact").eq("group_id", group_id).execute()
    # Считаем события по Telegram chat_id, а не по UUID группы
    group_res = get_supabase_admin().table("groups").select("chat_id").eq("id", group_id).maybe_single().execute()
    tg_chat_id = group_res.data["chat_id"] if group_res.data else None
    if tg_chat_id:
        events_res = get_supabase_admin().table("events").select("id", count="exact").eq("chat_id", tg_chat_id).execute()
        events_count = events_res.count or 0
    else:
        events_count = 0

    return (
        f"📊 *Статистика группы*\n\n"
        f"👥 Участников: *{members_count}*\n"
        f"⚠️ Варнов выдано: *{warns_count}*\n"
        f"📅 Событий создано: *{events_count}*"
    )
