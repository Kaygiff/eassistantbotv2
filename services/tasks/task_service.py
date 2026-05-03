"""
services/tasks/task_service.py — Создание и управление задачами и напоминаниями.
"""

from __future__ import annotations
import re
import uuid
import logging
from datetime import datetime, timezone

from db.supabase import supabase_admin
from auth.session import get_fsm_state, set_fsm_state, set_fsm_data, get_fsm_data, clear_fsm_state, clear_fsm_data
from brain.context import BrainContext

logger = logging.getLogger(__name__)


async def create_task_from_text(user_id: str, text: str, language: str) -> str:
    """Создаёт задачу из текстового запроса."""
    title = re.sub(
        r"(создать задачу|добавить задачу|новая задача|/todo)\s*",
        "", text, flags=re.IGNORECASE
    ).strip()

    if not title:
        await set_fsm_state(user_id, "task:awaiting_title")
        return "📝 Введи название задачи:"

    task_id = str(uuid.uuid4())
    supabase_admin.table("tasks").insert({
        "id": task_id,
        "user_id": user_id,
        "type": "todo",
        "title": title,
        "priority": "medium",
        "status": "pending",
    }).execute()

    return f"✅ Задача добавлена:\n📌 *{title}*"


async def get_task_list(user_id: str, language: str) -> str:
    """Возвращает список активных задач пользователя."""
    res = (
        supabase_admin.table("tasks")
        .select("*")
        .eq("user_id", user_id)
        .eq("status", "pending")
        .eq("type", "todo")
        .order("created_at", desc=False)
        .limit(20)
        .execute()
    )
    tasks = res.data or []

    if not tasks:
        return "📭 У тебя нет активных задач."

    priority_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}
    lines = ["📋 *Мои задачи:*\n"]
    for i, task in enumerate(tasks, 1):
        icon = priority_icon.get(task["priority"], "⚪")
        due = f" · ⏰ {task['due_at'][:10]}" if task.get("due_at") else ""
        lines.append(f"{i}. {icon} {task['title']}{due}")

    return "\n".join(lines)


async def mark_task_done(user_id: str, text: str, language: str) -> str:
    """Помечает задачу как выполненную по номеру или названию."""
    # Пробуем найти номер
    match = re.search(r"\d+", text)
    if match:
        task_num = int(match.group())
        res = (
            supabase_admin.table("tasks")
            .select("id, title")
            .eq("user_id", user_id)
            .eq("status", "pending")
            .eq("type", "todo")
            .order("created_at")
            .execute()
        )
        tasks = res.data or []
        if 1 <= task_num <= len(tasks):
            task = tasks[task_num - 1]
            supabase_admin.table("tasks").update({"status": "done"}).eq("id", task["id"]).execute()
            return f"✅ Задача выполнена:\n~~{task['title']}~~"

    return "❌ Задача не найдена. Используй номер из списка /tasks"


async def create_reminder_from_text(user_id: str, text: str, language: str) -> str:
    """Создаёт напоминание из текстового запроса."""
    title = re.sub(
        r"(напомни|установи напоминание|напоминание|/remind)\s*",
        "", text, flags=re.IGNORECASE
    ).strip()

    if not title:
        await set_fsm_state(user_id, "reminder:awaiting_text")
        return "⏰ Введи текст напоминания:"

    # Запрашиваем время
    await set_fsm_state(user_id, "reminder:awaiting_time")
    await set_fsm_data(user_id, {"title": title})
    return f"⏰ Напоминание: *{title}*\n\nВведи дату и время (ДД.ММ.ГГГГ ЧЧ:ММ):"


async def handle_task_fsm(ctx: BrainContext, bot, state: str) -> bool:
    """Обрабатывает FSM-ввод для задач и напоминаний."""
    user_id = str(ctx.user.id)
    text = ctx.text.strip()

    if state == "task:awaiting_title":
        if not text:
            return True
        task_id = str(uuid.uuid4())
        supabase_admin.table("tasks").insert({
            "id": task_id, "user_id": user_id,
            "type": "todo", "title": text,
            "priority": "medium", "status": "pending",
        }).execute()
        await clear_fsm_state(user_id)
        await bot.send_message(ctx.chat_id, f"✅ Задача добавлена:\n📌 *{text}*", parse_mode="Markdown")
        return True

    if state == "reminder:awaiting_text":
        await set_fsm_state(user_id, "reminder:awaiting_time")
        await set_fsm_data(user_id, {"title": text})
        await bot.send_message(ctx.chat_id, f"⏰ Напоминание: *{text}*\n\nВведи дату и время (ДД.ММ.ГГГГ ЧЧ:ММ):", parse_mode="Markdown")
        return True

    if state == "reminder:awaiting_time":
        data = await get_fsm_data(user_id)
        title = data.get("title", "Напоминание")
        try:
            due_at = datetime.strptime(text, "%d.%m.%Y %H:%M").replace(tzinfo=timezone.utc)
        except ValueError:
            await bot.send_message(ctx.chat_id, "⚠️ Формат: ДД.ММ.ГГГГ ЧЧ:ММ (например: 15.03.2025 09:00)")
            return True

        task_id = str(uuid.uuid4())
        supabase_admin.table("tasks").insert({
            "id": task_id, "user_id": user_id,
            "type": "reminder", "title": title,
            "due_at": due_at.isoformat(),
            "priority": "medium", "status": "pending",
            "reminder_sent": False,
        }).execute()
        await clear_fsm_state(user_id)
        await clear_fsm_data(user_id)
        await bot.send_message(ctx.chat_id, f"✅ Напоминание установлено:\n⏰ *{title}*\n📅 {text}", parse_mode="Markdown")
        return True

    return False
