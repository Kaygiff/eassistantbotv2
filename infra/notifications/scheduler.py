"""
notifications/scheduler.py — Планировщик уведомлений.
Ставит задачи в Celery-очередь с нужным временем.
"""

from __future__ import annotations
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def schedule_reminder(task_id: str, run_at: datetime) -> None:
    """
    Ставит задачу отправки напоминания в Celery-очередь с ETA.
    """
    from infra.queue.tasks import send_reminder
    send_reminder.apply_async(
        args=[task_id],
        eta=run_at,
        queue="high",
    )
    logger.info(f"[Scheduler] Reminder {task_id} scheduled for {run_at}")


def schedule_broadcast(
    text: str,
    language: str | None = None,
    run_at: datetime | None = None,
) -> None:
    """
    Ставит задачу массовой рассылки в Celery.
    run_at=None — немедленно.
    """
    from infra.queue.tasks import send_broadcast
    kwargs = dict(text=text, language=language)
    if run_at:
        send_broadcast.apply_async(kwargs=kwargs, eta=run_at, queue="low")
    else:
        send_broadcast.delay(**kwargs)
    logger.info(f"[Scheduler] Broadcast scheduled (lang={language}, at={run_at})")
