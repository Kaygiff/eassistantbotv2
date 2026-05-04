"""
monitoring/sentry.py — Sentry конфигурация и утилиты.
Вынесено из metrics.py для чистоты импортов.
"""

from __future__ import annotations
import os
from typing import Any

import sentry_sdk

SENTRY_DSN = os.getenv("SENTRY_DSN")
APP_ENV = os.getenv("APP_ENV", "development")


def set_user_context(user_id: str, telegram_id: int | None = None) -> None:
    """Устанавливает контекст пользователя для текущего Sentry-события."""
    sentry_sdk.set_user({"id": user_id, "telegram_id": str(telegram_id) if telegram_id else None})


def set_tag(key: str, value: str) -> None:
    """Добавляет тег к текущему Sentry-событию."""
    sentry_sdk.set_tag(key, value)


def set_extra(key: str, value: Any) -> None:
    """Добавляет дополнительные данные к текущему Sentry-событию."""
    sentry_sdk.set_extra(key, value)


def capture_message(message: str, level: str = "info") -> None:
    """Отправляет произвольное сообщение в Sentry."""
    sentry_sdk.capture_message(message, level=level)


def new_scope(user_id: str | None = None, intent: str | None = None):
    """Context manager для изолированного Sentry-scope."""
    scope = sentry_sdk.new_scope()
    if user_id:
        scope.set_user({"id": user_id})
    if intent:
        scope.set_tag("intent", intent)
    return scope
