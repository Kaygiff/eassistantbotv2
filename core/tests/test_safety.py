"""
tests/test_safety.py — Тесты safety слоя.
"""

import pytest
from unittest.mock import AsyncMock, patch
from infra.safety.rate_limiter import is_rate_limited, reset_rate_limit


class TestRateLimiter:

    @pytest.mark.asyncio
    async def test_not_limited_initially(self, fake_redis):
        with patch("safety.rate_limiter.get_redis", return_value=fake_redis):
            result = await is_rate_limited("user_123", "message")
            assert result is False

    @pytest.mark.asyncio
    async def test_limited_after_threshold(self, fake_redis):
        with patch("safety.rate_limiter.get_redis", return_value=fake_redis):
            # Симулируем 31 запрос (лимит 30)
            for _ in range(31):
                result = await is_rate_limited("user_456", "message")
            assert result is True

    @pytest.mark.asyncio
    async def test_reset_clears_limit(self, fake_redis):
        with patch("safety.rate_limiter.get_redis", return_value=fake_redis):
            for _ in range(31):
                await is_rate_limited("user_789", "message")

            await reset_rate_limit("user_789", "message")
            result = await is_rate_limited("user_789", "message")
            assert result is False

    @pytest.mark.asyncio
    async def test_different_actions_independent(self, fake_redis):
        with patch("safety.rate_limiter.get_redis", return_value=fake_redis):
            # Исчерпываем лимит AI
            for _ in range(11):
                await is_rate_limited("user_abc", "ai_chat")

            # Лимит сообщений не тронут
            result = await is_rate_limited("user_abc", "message")
            assert result is False


class TestUserBan:

    @pytest.mark.asyncio
    async def test_not_banned_user(self, sample_user):
        from infra.safety.user_ban import is_banned
        result = await is_banned(sample_user)
        assert result is False

    @pytest.mark.asyncio
    async def test_banned_user(self, sample_user):
        from infra.safety.user_ban import is_banned
        sample_user.is_banned = True
        sample_user.ban_until = None
        result = await is_banned(sample_user)
        assert result is True

    @pytest.mark.asyncio
    async def test_expired_ban_auto_lifted(self, sample_user, mocker):
        from datetime import datetime, timezone, timedelta
        from infra.safety.user_ban import is_banned

        sample_user.is_banned = True
        sample_user.ban_until = datetime.now(timezone.utc) - timedelta(hours=1)

        mock_lift = mocker.patch("safety.user_ban.lift_ban", new_callable=AsyncMock)
        result = await is_banned(sample_user)

        assert result is False
        mock_lift.assert_called_once_with(str(sample_user.id))
