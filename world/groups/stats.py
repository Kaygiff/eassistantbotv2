"""
groups/stats.py — Статистика группы.
"""

from __future__ import annotations
from infra.db.supabase import get_supabase_admin


async def get_group_stats(group_id: str, language: str) -> str:
    if not group_id:
        return "❌ Группа не найдена."

    db = get_supabase_admin()

    members_res = db.table("group_members").select("id", count="exact").eq("group_id", group_id).execute()
    warns_res = db.table("group_warns").select("id", count="exact").eq("group_id", group_id).execute()

    members_count = members_res.count or 0
    warns_count = warns_res.count or 0

    # events хранит Telegram chat_id (число), а не UUID группы — получаем его отдельно
    events_count = 0
    try:
        group_res = db.table("groups").select("chat_id").eq("id", group_id).maybe_single().execute()
        if group_res.data:
            tg_chat_id = group_res.data["chat_id"]
            events_res = db.table("events").select("id", count="exact").eq("chat_id", tg_chat_id).execute()
            events_count = events_res.count or 0
    except Exception:
        pass

    return (
        f"📊 *Статистика группы*\n\n"
        f"👥 Участников: *{members_count}*\n"
        f"⚠️ Варнов выдано: *{warns_count}*\n"
        f"📅 Событий создано: *{events_count}*"
    )
