"""
auth/consent.py — Неявное согласие с условиями использования.
Факт отправки первого сообщения = согласие с ToS.
Явного экрана подтверждения нет (по документации).
"""

from __future__ import annotations
from datetime import datetime, timezone

from api.audit.logger import log_action


async def record_implicit_consent(user_id: str, telegram_id: int, ip: str | None = None) -> None:
    """
    Фиксирует факт неявного согласия пользователя с ToS.
    Вызывается один раз при первом сообщении нового пользователя.
    """
    await log_action(
        user_id=user_id,
        action="implicit_consent",
        details={
            "telegram_id": telegram_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "method": "first_message",
        },
        ip_address=ip,
    )


def has_consented(user) -> bool:
    """
    Пользователь считается согласившимся если его профиль существует.
    Профиль создаётся только после онбординга.
    """
    return user is not None and user.assistant_name != "Ассистент"
