"""
queue/tasks.py — Все Celery-задачи.
"""

from __future__ import annotations
import asyncio
import logging
import os

from infra.queue.app import app

logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")


def _run(coro):
    """Запускает async корутину из синхронного Celery-таска."""
    return asyncio.get_event_loop().run_until_complete(coro)


# ---------------------------------------------------------------------------
# Уведомления
# ---------------------------------------------------------------------------

@app.task(name="queue.tasks.send_single_notification", queue="high", max_retries=3)
def send_single_notification(telegram_id: int, text: str, parse_mode: str = "Markdown") -> None:
    """Отправляет сообщение одному пользователю."""
    import httpx
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    with httpx.Client() as client:
        resp = client.post(url, json={
            "chat_id": telegram_id,
            "text": text,
            "parse_mode": parse_mode,
        })
        if not resp.is_success:
            logger.warning(f"[Task] Failed to send to {telegram_id}: {resp.text}")


@app.task(name="queue.tasks.send_broadcast", queue="low")
def send_broadcast(text: str, language: str | None = None, parse_mode: str = "Markdown", limit: int = 1000) -> dict:
    """
    Массовая рассылка пользователям.
    language=None — всем, иначе фильтрует по языку.
    """
    from infra.db.supabase import supabase_admin
    from api.audit.logger import log_action

    query = supabase_admin.table("users").select("telegram_id").eq("is_banned", False).limit(limit)
    if language:
        query = query.eq("language", language)
    res = query.execute()
    users = res.data or []

    sent = 0
    failed = 0
    import httpx
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    with httpx.Client() as client:
        for user in users:
            try:
                resp = client.post(url, json={
                    "chat_id": user["telegram_id"],
                    "text": text,
                    "parse_mode": parse_mode,
                })
                if resp.is_success:
                    sent += 1
                else:
                    failed += 1
            except Exception as e:
                failed += 1
                logger.warning(f"[Broadcast] Error for {user['telegram_id']}: {e}")

    _run(log_action(
        action="broadcast",
        details={"sent": sent, "failed": failed, "language": language, "text_preview": text[:100]},
    ))
    logger.info(f"[Broadcast] Done: sent={sent}, failed={failed}")
    return {"sent": sent, "failed": failed}


# ---------------------------------------------------------------------------
# Напоминания
# ---------------------------------------------------------------------------

@app.task(name="queue.tasks.send_reminder", queue="high")
def send_reminder(task_id: str) -> None:
    """Отправляет напоминание пользователю."""
    from infra.db.supabase import supabase_admin

    res = (
        supabase_admin.table("tasks")
        .select("*, users(telegram_id, language)")
        .eq("id", task_id)
        .maybe_single()
        .execute()
    )
    if not res.data:
        return

    task = res.data
    user = task.get("users", {})
    telegram_id = user.get("telegram_id")
    lang = user.get("language", "ru")

    if not telegram_id:
        return

    from core.i18n.loader import t
    text = f"⏰ *Напоминание*\n\n{task['title']}"
    send_single_notification.delay(telegram_id, text)

    # Помечаем как отправленное
    supabase_admin.table("tasks").update({"reminder_sent": True}).eq("id", task_id).execute()


@app.task(name="queue.tasks.check_and_send_reminders", queue="high")
def check_and_send_reminders() -> None:
    """Проверяет задачи с наступившим временем напоминания и ставит в очередь."""
    from datetime import datetime, timezone
    from infra.db.supabase import supabase_admin

    now = datetime.now(timezone.utc).isoformat()
    res = (
        supabase_admin.table("tasks")
        .select("id")
        .eq("type", "reminder")
        .eq("status", "pending")
        .eq("reminder_sent", False)
        .lte("due_at", now)
        .execute()
    )
    for task in (res.data or []):
        send_reminder.delay(task["id"])

    logger.info(f"[Reminders] Queued {len(res.data or [])} reminders")


# ---------------------------------------------------------------------------
# Питомцы
# ---------------------------------------------------------------------------

@app.task(name="queue.tasks.pet_decay_tick", queue="low")
def pet_decay_tick() -> None:
    """Деградация питомцев. Логика в virtual_world/pets/decay.py."""
    from world.virtual_world.pets.decay import process_all_pets
    count = _run(process_all_pets())
    logger.info(f"[PetDecay] Processed {count} pets")


# ---------------------------------------------------------------------------
# Экономика
# ---------------------------------------------------------------------------

@app.task(name="queue.tasks.reset_expired_streaks", queue="low")
def reset_expired_streaks() -> None:
    """
    Сбрасывает стрик ежедневного бонуса у пользователей,
    которые пропустили день (last_bonus_at < вчера).
    """
    from datetime import datetime, timedelta, timezone
    from infra.db.supabase import supabase_admin

    yesterday = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
    res = (
        supabase_admin.table("daily_bonuses")
        .select("user_id")
        .lt("last_bonus_at", yesterday)
        .gt("streak_days", 0)
        .execute()
    )
    ids = [r["user_id"] for r in (res.data or [])]
    if ids:
        supabase_admin.table("daily_bonuses").update({"streak_days": 0}).in_("user_id", ids).execute()
    logger.info(f"[DailyBonus] Reset streaks for {len(ids)} users")
