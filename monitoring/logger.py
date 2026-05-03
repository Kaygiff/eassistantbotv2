"""
monitoring/logger.py — Структурный логгер для всего приложения.
Тонкая обёртка над structlog. Используется во всех модулях.

Использование:
    from monitoring.logger import get_logger
    logger = get_logger(__name__)
    logger.info("User registered", user_id=user_id, lang="ru")
"""

from __future__ import annotations
import structlog

# Алиас для удобного импорта
get_logger = structlog.get_logger


def bind_user(logger: structlog.BoundLogger, user_id: str, telegram_id: int | None = None) -> structlog.BoundLogger:
    """Привязывает контекст пользователя к логгеру."""
    return logger.bind(user_id=user_id, telegram_id=telegram_id)


def bind_request(logger: structlog.BoundLogger, intent: str, chat_id: int) -> structlog.BoundLogger:
    """Привязывает контекст запроса к логгеру."""
    return logger.bind(intent=intent, chat_id=chat_id)
