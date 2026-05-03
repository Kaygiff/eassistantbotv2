"""
tests/test_auth.py — Тесты auth модуля.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestSession:

    @pytest.mark.asyncio
    async def test_set_and_get_session(self, fake_redis):
        with patch("auth.session.get_redis", return_value=fake_redis):
            from auth.session import set_session, get_session

            data = {"lang": "ru", "step": 2}
            await set_session("user-123", data)
            result = await get_session("user-123")
            assert result == data

    @pytest.mark.asyncio
    async def test_get_empty_session(self, fake_redis):
        with patch("auth.session.get_redis", return_value=fake_redis):
            from auth.session import get_session
            result = await get_session("nonexistent-user")
            assert result == {}

    @pytest.mark.asyncio
    async def test_update_session(self, fake_redis):
        with patch("auth.session.get_redis", return_value=fake_redis):
            from auth.session import set_session, update_session, get_session

            await set_session("user-456", {"lang": "ru"})
            await update_session("user-456", step=3)
            result = await get_session("user-456")
            assert result["lang"] == "ru"
            assert result["step"] == 3

    @pytest.mark.asyncio
    async def test_fsm_state(self, fake_redis):
        with patch("auth.session.get_redis", return_value=fake_redis):
            from auth.session import set_fsm_state, get_fsm_state, clear_fsm_state

            await set_fsm_state("user-789", "onboarding:language")
            state = await get_fsm_state("user-789")
            assert state == "onboarding:language"

            await clear_fsm_state("user-789")
            state = await get_fsm_state("user-789")
            assert state is None


class TestIdentity:

    @pytest.mark.asyncio
    async def test_get_user_by_telegram_id_not_found(self, mock_supabase):
        mock_supabase.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = None

        from auth.identity import get_user_by_telegram_id
        result = await get_user_by_telegram_id(999999)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_or_create_user_existing(self, mock_supabase, sample_user, mocker):
        mocker.patch(
            "auth.identity.get_user_by_telegram_id",
            new_callable=AsyncMock,
            return_value=sample_user,
        )

        from auth.identity import get_or_create_user
        user, is_new = await get_or_create_user(telegram_id=123456789)
        assert user.telegram_id == 123456789
        assert is_new is False
