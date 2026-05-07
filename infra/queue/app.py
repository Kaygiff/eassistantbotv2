"""
queue/app.py — Celery приложение.
Две очереди: high (уведомления, AI) и low (рассылки, decay питомцев).
"""

from __future__ import annotations
import os
from celery import Celery
from celery.schedules import crontab

BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1")
RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/2")

app = Celery(
    "eassistant",
    broker=BROKER_URL,
    backend=RESULT_BACKEND,
    include=["queue.tasks"],
)

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_routes={
        "queue.tasks.send_broadcast": {"queue": "low"},
        "queue.tasks.send_single_notification": {"queue": "high"},
        "queue.tasks.pet_decay_tick": {"queue": "low"},
        "queue.tasks.send_reminder": {"queue": "high"},
        "queue.tasks.reset_daily_bonus": {"queue": "low"},
    },
    beat_schedule={
        # Деградация питомцев — каждые 30 минут
        "pet-decay": {
            "task": "queue.tasks.pet_decay_tick",
            "schedule": 1800,
        },
        # Проверка и отправка напоминаний — каждую минуту
        "reminders-check": {
            "task": "queue.tasks.check_and_send_reminders",
            "schedule": 60,
        },
        # Сброс стрика ежедневного бонуса — каждый день в 00:05 UTC
        "reset-daily-bonus": {
            "task": "queue.tasks.reset_expired_streaks",
            "schedule": crontab(hour=0, minute=5),
        },
    },
)
