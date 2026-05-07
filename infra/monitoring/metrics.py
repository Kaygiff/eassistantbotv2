"""
monitoring/metrics.py — Метрики, Sentry, структурные логи.
Sentry: ошибки + performance tracing.
structlog: JSON-логи для Railway/Render.
"""

from __future__ import annotations
import os
import logging
import structlog
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.celery import CeleryIntegration

SENTRY_DSN = os.getenv("SENTRY_DSN")
APP_ENV = os.getenv("APP_ENV", "development")
LOG_LEVEL = os.getenv("APP_LOG_LEVEL", "INFO")


def init_sentry() -> None:
    """Инициализирует Sentry SDK. Вызывается один раз при старте."""
    if not SENTRY_DSN:
        return
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        environment=APP_ENV,
        integrations=[
            FastApiIntegration(),
            CeleryIntegration(),
        ],
        traces_sample_rate=0.2 if APP_ENV == "production" else 1.0,
        send_default_pii=False,
    )


def init_logging() -> None:
    """Настраивает structlog для JSON-вывода в production."""
    level = getattr(logging, LOG_LEVEL.upper(), logging.INFO)
    logging.basicConfig(level=level)

    if APP_ENV == "production":
        structlog.configure(
            processors=[
                structlog.stdlib.add_log_level,
                structlog.stdlib.add_logger_name,
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.JSONRenderer(),
            ],
            wrapper_class=structlog.make_filtering_bound_logger(level),
            logger_factory=structlog.PrintLoggerFactory(),
        )
    else:
        structlog.configure(
            processors=[
                structlog.stdlib.add_log_level,
                structlog.processors.TimeStamper(fmt="%H:%M:%S"),
                structlog.dev.ConsoleRenderer(),
            ],
            wrapper_class=structlog.make_filtering_bound_logger(level),
            logger_factory=structlog.PrintLoggerFactory(),
        )


def get_logger(name: str) -> structlog.BoundLogger:
    """Возвращает структурный логгер для модуля."""
    return structlog.get_logger(name)


def capture_exception(e: Exception, context: dict | None = None) -> None:
    """Отправляет исключение в Sentry с дополнительным контекстом."""
    if context:
        with sentry_sdk.push_scope() as scope:
            for k, v in context.items():
                scope.set_extra(k, v)
            sentry_sdk.capture_exception(e)
    else:
        sentry_sdk.capture_exception(e)


def set_sentry_user(user_id: str, telegram_id: int | None = None) -> None:
    """Привязывает пользователя к текущему Sentry-событию."""
    sentry_sdk.set_user({"id": user_id, "telegram_id": telegram_id})
