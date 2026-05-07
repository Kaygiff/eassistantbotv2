"""
ai_provider/hub.py — Центральный AI Provider Hub.
Управляет 8 провайдерами с Circuit Breaker и автоматическим fallback.

Порядок провайдеров:
  1. OpenAI GPT-4o (основной)
  2. Mistral
  3. DeepSeek
  4. Groq (Llama)
  5. Cohere
  6. Perplexity
  7. Qwen
  8. Yi

Circuit Breaker: если провайдер падает 3 раза подряд — отключается на 5 минут.
"""

from __future__ import annotations
import asyncio
import logging
import time
from typing import Any

from services.ai_provider.providers.openai import OpenAIProvider
from services.ai_provider.providers.mistral import MistralProvider
from services.ai_provider.providers.groq import GroqProvider
from services.ai_provider.providers.cohere import CohereProvider

logger = logging.getLogger(__name__)

CIRCUIT_BREAKER_THRESHOLD = 3    # сколько ошибок подряд
CIRCUIT_BREAKER_TIMEOUT = 300    # секунд (5 минут)


class CircuitBreaker:
    """Простой Circuit Breaker для одного провайдера."""

    def __init__(self, name: str):
        self.name = name
        self.failures = 0
        self.opened_at: float | None = None

    def is_open(self) -> bool:
        if self.opened_at is None:
            return False
        if time.monotonic() - self.opened_at > CIRCUIT_BREAKER_TIMEOUT:
            self.reset()
            return False
        return True

    def record_failure(self) -> None:
        self.failures += 1
        if self.failures >= CIRCUIT_BREAKER_THRESHOLD:
            self.opened_at = time.monotonic()
            logger.warning(f"[CircuitBreaker] {self.name} OPEN after {self.failures} failures")

    def record_success(self) -> None:
        if self.failures > 0:
            logger.info(f"[CircuitBreaker] {self.name} recovered")
        self.reset()

    def reset(self) -> None:
        self.failures = 0
        self.opened_at = None


class AIProviderHub:
    """
    Менеджер AI-провайдеров с Circuit Breaker и fallback.
    Singleton — создаётся один раз при старте.
    """

    def __init__(self):
        self._providers = [
            OpenAIProvider(),
            MistralProvider(),
            GroqProvider(),
            CohereProvider(),
        ]
        self._breakers = {p.name: CircuitBreaker(p.name) for p in self._providers}

    async def chat(
        self,
        messages: list[dict[str, str]],
        system: str | None = None,
        max_tokens: int = 1000,
        temperature: float = 0.7,
    ) -> tuple[str, str]:
        """
        Отправляет запрос к первому доступному провайдеру.
        Возвращает (response_text, provider_name).
        """
        for provider in self._providers:
            breaker = self._breakers[provider.name]

            if breaker.is_open():
                logger.debug(f"[Hub] Skipping {provider.name} (circuit open)")
                continue

            if not provider.is_available():
                continue

            try:
                start = time.monotonic()
                result = await provider.chat(
                    messages=messages,
                    system=system,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
                elapsed = round((time.monotonic() - start) * 1000)
                breaker.record_success()
                logger.info(f"[Hub] {provider.name} responded in {elapsed}ms")
                return result, provider.name

            except Exception as e:
                logger.warning(f"[Hub] {provider.name} failed: {e}")
                breaker.record_failure()
                continue

        raise RuntimeError("All AI providers failed or unavailable")

    def get_status(self) -> list[dict[str, Any]]:
        """Возвращает статус всех провайдеров (для EAdmin дашборда)."""
        return [
            {
                "name": p.name,
                "available": p.is_available(),
                "circuit_open": self._breakers[p.name].is_open(),
                "failures": self._breakers[p.name].failures,
            }
            for p in self._providers
        ]


# Singleton
_hub: AIProviderHub | None = None


def get_hub() -> AIProviderHub:
    global _hub
    if _hub is None:
        _hub = AIProviderHub()
    return _hub
