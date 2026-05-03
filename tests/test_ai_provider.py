"""
tests/test_ai_provider.py — Тесты AI Provider Hub и Circuit Breaker.
"""

import pytest
from unittest.mock import AsyncMock, patch


class TestCircuitBreaker:

    def test_initially_closed(self):
        from ai_provider.hub import CircuitBreaker
        cb = CircuitBreaker("test")
        assert cb.is_open() is False

    def test_opens_after_threshold(self):
        from ai_provider.hub import CircuitBreaker, CIRCUIT_BREAKER_THRESHOLD
        cb = CircuitBreaker("test")
        for _ in range(CIRCUIT_BREAKER_THRESHOLD):
            cb.record_failure()
        assert cb.is_open() is True

    def test_resets_after_success(self):
        from ai_provider.hub import CircuitBreaker, CIRCUIT_BREAKER_THRESHOLD
        cb = CircuitBreaker("test")
        for _ in range(CIRCUIT_BREAKER_THRESHOLD):
            cb.record_failure()
        assert cb.is_open() is True
        cb.record_success()
        assert cb.failures == 0

    def test_closes_after_timeout(self):
        import time
        from ai_provider.hub import CircuitBreaker, CIRCUIT_BREAKER_THRESHOLD
        cb = CircuitBreaker("test")
        for _ in range(CIRCUIT_BREAKER_THRESHOLD):
            cb.record_failure()
        # Эмулируем истечение таймаута
        cb.opened_at = time.monotonic() - 9999
        assert cb.is_open() is False


class TestOpenAIProvider:

    def test_not_available_without_key(self):
        import os
        with patch.dict(os.environ, {"OPENAI_API_KEY": ""}):
            from ai_provider.providers.openai import OpenAIProvider
            provider = OpenAIProvider()
            provider._key = ""
            assert provider.is_available() is False

    def test_available_with_key(self):
        from ai_provider.providers.openai import OpenAIProvider
        provider = OpenAIProvider()
        provider._key = "sk-test-key"
        assert provider.is_available() is True


class TestAIHub:

    @pytest.mark.asyncio
    async def test_hub_uses_first_available(self):
        from ai_provider.hub import AIProviderHub

        hub = AIProviderHub()

        # Мокируем первый провайдер
        hub._providers[0].is_available = lambda: True
        hub._providers[0].chat = AsyncMock(return_value="Test response")

        result, provider_name = await hub.chat(
            messages=[{"role": "user", "content": "Hello"}]
        )
        assert result == "Test response"

    @pytest.mark.asyncio
    async def test_hub_skips_open_circuit(self):
        from ai_provider.hub import AIProviderHub, CIRCUIT_BREAKER_THRESHOLD

        hub = AIProviderHub()

        # Открываем circuit первого провайдера
        for _ in range(CIRCUIT_BREAKER_THRESHOLD):
            hub._breakers[hub._providers[0].name].record_failure()

        # Мокируем второй провайдер
        hub._providers[1].is_available = lambda: True
        hub._providers[1].chat = AsyncMock(return_value="Fallback response")

        # Блокируем остальных
        for i in range(2, len(hub._providers)):
            hub._providers[i].is_available = lambda: False

        result, provider_name = await hub.chat(
            messages=[{"role": "user", "content": "Hello"}]
        )
        assert result == "Fallback response"
        assert provider_name == hub._providers[1].name
