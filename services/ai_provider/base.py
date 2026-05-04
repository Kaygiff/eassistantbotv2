"""
ai_provider/base.py — Абстрактный базовый класс для AI-провайдеров.
"""

from __future__ import annotations
from abc import ABC, abstractmethod


class BaseAIProvider(ABC):
    """Базовый класс. Все провайдеры наследуют от него."""

    name: str = "base"

    @abstractmethod
    def is_available(self) -> bool:
        """Возвращает True если API ключ настроен."""
        ...

    @abstractmethod
    async def chat(
        self,
        messages: list[dict[str, str]],
        system: str | None = None,
        max_tokens: int = 1000,
        temperature: float = 0.7,
    ) -> str:
        """
        Отправляет чат-запрос и возвращает текст ответа.
        messages = [{"role": "user"|"assistant", "content": "..."}]
        """
        ...
