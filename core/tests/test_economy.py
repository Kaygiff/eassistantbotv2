"""
tests/test_economy.py — Тесты кошелька и транзакций.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestWallet:

    @pytest.mark.asyncio
    async def test_get_balance(self, mock_supabase):
        mock_supabase.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = {
            "balance": 500
        }
        from world.economy.wallet import get_balance
        balance = await get_balance("user-uuid-123")
        assert balance == 500

    @pytest.mark.asyncio
    async def test_get_balance_no_wallet(self, mock_supabase):
        mock_supabase.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = None
        from world.economy.wallet import get_balance
        balance = await get_balance("user-uuid-123")
        assert balance == 0

    @pytest.mark.asyncio
    async def test_credit_increases_balance(self, mock_supabase, mocker):
        mocker.patch("economy.wallet.get_balance", return_value=100)
        mocker.patch("economy.wallet.log_ecoin_transaction", new_callable=AsyncMock)

        update_mock = MagicMock()
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute = MagicMock()
        mock_supabase.table.return_value.insert.return_value.execute = MagicMock()

        from world.economy.wallet import credit
        new_balance = await credit("user-uuid", 200, "daily_bonus")
        assert new_balance == 300

    @pytest.mark.asyncio
    async def test_debit_success(self, mock_supabase, mocker):
        mocker.patch("economy.wallet.get_balance", return_value=500)
        mocker.patch("economy.wallet.log_ecoin_transaction", new_callable=AsyncMock)
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute = MagicMock()
        mock_supabase.table.return_value.insert.return_value.execute = MagicMock()

        from world.economy.wallet import debit
        success, new_balance = await debit("user-uuid", 200, "casino_bet")
        assert success is True
        assert new_balance == 300

    @pytest.mark.asyncio
    async def test_debit_insufficient_funds(self, mock_supabase, mocker):
        mocker.patch("economy.wallet.get_balance", return_value=50)

        from world.economy.wallet import debit
        success, balance = await debit("user-uuid", 200, "casino_bet")
        assert success is False
        assert balance == 50


class TestDailyBonus:

    @pytest.mark.asyncio
    async def test_streak_increases(self, mock_supabase, mocker):
        from datetime import datetime, timezone, timedelta

        yesterday = (datetime.now(timezone.utc) - timedelta(hours=20)).isoformat()
        mock_supabase.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = {
            "streak_days": 3,
            "last_bonus_at": yesterday,
            "total_bonuses_earned": 600,
        }
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute = MagicMock()
        mocker.patch("economy.daily.credit", new_callable=AsyncMock, return_value=800)

        from world.economy.daily import claim_daily_bonus
        result = await claim_daily_bonus("user-uuid", "ru")
        assert "бонус" in result.lower() or "+" in result

    @pytest.mark.asyncio
    async def test_already_claimed_today(self, mock_supabase):
        from datetime import datetime, timezone

        today = datetime.now(timezone.utc).isoformat()
        mock_supabase.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = {
            "streak_days": 5,
            "last_bonus_at": today,
            "total_bonuses_earned": 1000,
        }

        from world.economy.daily import claim_daily_bonus
        result = await claim_daily_bonus("user-uuid", "ru")
        assert "уже" in result.lower() or "tomorrow" in result.lower()
