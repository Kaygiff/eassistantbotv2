"""
brain/context.py — Объект контекста запроса.
Передаётся через весь pipeline: Brain → Handler → Service.
Содержит всё необходимое для обработки без лишних запросов к БД.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Optional

from bot.brain.intent import Intent
from core.models.user import User


@dataclass
class BrainContext:
    """
    Контекст одного входящего запроса.

    Создаётся в Brain.process() и передаётся в хэндлер.
    Хэндлер не делает лишних запросов к БД — всё уже есть в контексте.
    """

    # --- Telegram ---
    telegram_id: int
    chat_id: int
    message_id: int
    text: str
    is_group: bool = False
    is_voice: bool = False
    voice_file_id: Optional[str] = None
    reply_to_user_telegram_id: Optional[int] = None  # @ упоминание или reply
    reply_to_message_id: Optional[int] = None         # message_id для реплая в чат

    # --- Telegram-данные отправителя (из Message.from_user) ---
    tg_username: Optional[str] = None
    tg_first_name: Optional[str] = None
    tg_last_name: Optional[str] = None
    tg_is_premium: bool = False
    tg_locale: Optional[str] = None

    # --- Пользователь ---
    user: Optional[User] = None            # None до get_or_create
    language: str = "ru"

    # --- Intent ---
    intent: Intent = Intent.UNKNOWN
    intent_confidence: str = "keyword"     # "keyword" | "ai" | "fallback"

    # --- Группа ---
    group_id: Optional[str] = None         # UUID группы (для групповых чатов)

    # --- Дополнительные данные ---
    # Хэндлеры могут добавлять сюда промежуточные данные
    extra: dict[str, Any] = field(default_factory=dict)

    # --- Флаги ---
    is_new_user: bool = False              # True если пользователь только что создан
    is_command: bool = False               # True если сообщение начинается с /

    @property
    def user_id(self) -> Optional[str]:
        """UUID пользователя или None если user не загружен."""
        return str(self.user.id) if self.user else None

    @property
    def assistant_name(self) -> str:
        return self.user.assistant_name if self.user else "Ассистент"

    def set_intent(self, intent: Intent, confidence: str = "keyword") -> None:
        self.intent = intent
        self.intent_confidence = confidence

    def __repr__(self) -> str:
        return (
            f"BrainContext(tg={self.telegram_id}, "
            f"intent={self.intent.value}, "
            f"is_group={self.is_group}, "
            f"lang={self.language})"
        )
