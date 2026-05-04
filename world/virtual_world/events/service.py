"""
virtual_world/events/service.py — Создание и управление событиями.
"""

from __future__ import annotations
import uuid
import logging
from datetime import datetime, timezone

from infra.db.supabase import supabase_admin
from bot.brain.context import BrainContext
from api.auth.session import set_fsm_state, set_fsm_data, get_fsm_data, clear_fsm_state, clear_fsm_data

logger = logging.getLogger(__name__)


async def start_event_creation(ctx: BrainContext, bot) -> None:
    """Запускает FSM создания события."""
    await set_fsm_state(str(ctx.user.id), "event:awaiting_title")
    await bot.send_message(ctx.chat_id, "📅 *Создание события*\n\nВведи название события:", parse_mode="Markdown")


async def get_events_list(chat_id: int, language: str) -> str:
    """Возвращает список предстоящих событий в группе."""
    from datetime import timezone
    now = datetime.now(timezone.utc).isoformat()
    res = (
        supabase_admin.table("events")
        .select("*, users!creator_id(first_name, username)")
        .eq("chat_id", chat_id)
        .gte("event_at", now)
        .order("event_at")
        .limit(10)
        .execute()
    )
    events = res.data or []

    if not events:
        return "📅 Предстоящих событий нет."

    lines = ["📅 *Предстоящие события:*\n"]
    for ev in events:
        creator = ev.get("users!creator_id") or {}
        creator_name = creator.get("first_name") or f"@{creator.get('username', '?')}"
        dt = ev["event_at"][:16].replace("T", " ")
        lines.append(f"🗓 *{ev['title']}*\n📆 {dt} · 👤 {creator_name}")

    return "\n\n".join(lines)


async def join_event(ctx: BrainContext, bot) -> str:
    """Присоединяет пользователя к событию."""
    import re
    match = re.search(r"\d+", ctx.text)
    if not match:
        return "❓ Укажи номер события из списка /events"

    # Упрощённо — берём первое предстоящее событие
    now = datetime.now(timezone.utc).isoformat()
    res = (
        supabase_admin.table("events")
        .select("id, title")
        .eq("chat_id", ctx.chat_id)
        .gte("event_at", now)
        .order("event_at")
        .limit(1)
        .execute()
    )
    if not res.data:
        return "📅 Нет доступных событий."

    event = res.data[0]
    user_id = str(ctx.user.id)

    supabase_admin.table("event_participants").upsert({
        "event_id": event["id"],
        "user_id": user_id,
        "status": "accepted",
        "joined_at": datetime.now(timezone.utc).isoformat(),
    }).execute()

    return f"✅ Ты присоединился(ась) к событию *{event['title']}*!"


async def handle_event_fsm(ctx: BrainContext, bot, state: str) -> bool:
    """FSM создания события."""
    user_id = str(ctx.user.id)
    text = ctx.text.strip()

    if state == "event:awaiting_title":
        await set_fsm_state(user_id, "event:awaiting_date")
        await set_fsm_data(user_id, {"title": text})
        await bot.send_message(ctx.chat_id, f"📅 Событие: *{text}*\n\nВведи дату и время (ДД.ММ.ГГГГ ЧЧ:ММ):", parse_mode="Markdown")
        return True

    if state == "event:awaiting_date":
        try:
            dt = datetime.strptime(text, "%d.%m.%Y %H:%M").replace(tzinfo=timezone.utc)
        except ValueError:
            await bot.send_message(ctx.chat_id, "⚠️ Формат: ДД.ММ.ГГГГ ЧЧ:ММ")
            return True

        await set_fsm_state(user_id, "event:awaiting_description")
        await set_fsm_data(user_id, {**(await get_fsm_data(user_id)), "event_at": dt.isoformat()})
        await bot.send_message(ctx.chat_id, "📝 Добавь описание (или напиши *-* чтобы пропустить):", parse_mode="Markdown")
        return True

    if state == "event:awaiting_description":
        data = await get_fsm_data(user_id)
        description = text if text != "-" else None

        supabase_admin.table("events").insert({
            "id": str(uuid.uuid4()),
            "creator_id": user_id,
            "chat_id": ctx.chat_id,
            "title": data["title"],
            "description": description,
            "event_at": data["event_at"],
            "type": "open",
        }).execute()

        await clear_fsm_state(user_id)
        await clear_fsm_data(user_id)
        await bot.send_message(ctx.chat_id, f"✅ Событие *{data['title']}* создано!", parse_mode="Markdown")
        return True

    return False
