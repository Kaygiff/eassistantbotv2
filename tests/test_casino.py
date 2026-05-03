"""
tests/test_casino.py — Тесты игр казино.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestSlots:

    @pytest.mark.asyncio
    async def test_slots_returns_result(self, mock_supabase, mocker):
        mocker.patch("casino.games.slots.debit", new_callable=AsyncMock, return_value=(True, 800))
        mocker.patch("casino.games.slots.credit", new_callable=AsyncMock, return_value=1000)
        mock_supabase.table.return_value.insert.return_value.execute = MagicMock()

        from casino.games.slots import play_slots
        result = await play_slots("user-uuid", 100, "ru")

        assert "🎰" in result
        assert "Слоты" in result

    @pytest.mark.asyncio
    async def test_slots_insufficient_funds(self, mock_supabase, mocker):
        mocker.patch("casino.games.slots.debit", new_callable=AsyncMock, return_value=(False, 50))

        from casino.games.slots import play_slots
        result = await play_slots("user-uuid", 100, "ru")
        assert "50" in result  # показывает текущий баланс


class TestBlackjack:

    @pytest.mark.asyncio
    async def test_blackjack_returns_result(self, mock_supabase, mocker):
        mocker.patch("casino.games.blackjack.debit", new_callable=AsyncMock, return_value=(True, 900))
        mocker.patch("casino.games.blackjack.credit", new_callable=AsyncMock, return_value=1100)
        mock_supabase.table.return_value.insert.return_value.execute = MagicMock()

        from casino.games.blackjack import play_blackjack
        result = await play_blackjack("user-uuid", 100, "ru")

        assert "Блэкджек" in result
        assert "карты" in result.lower() or "Карты" in result


class TestCrash:

    @pytest.mark.asyncio
    async def test_crash_returns_result(self, mock_supabase, mocker):
        mocker.patch("casino.games.crash.debit", new_callable=AsyncMock, return_value=(True, 900))
        mocker.patch("casino.games.crash.credit", new_callable=AsyncMock, return_value=1100)
        mock_supabase.table.return_value.insert.return_value.execute = MagicMock()

        from casino.games.crash import play_crash
        result = await play_crash("user-uuid", 100, "ru")

        assert "Краш" in result

    def test_crash_point_is_valid(self):
        from casino.games.crash import _generate_crash_point
        for _ in range(100):
            cp = _generate_crash_point()
            assert cp >= 1.0
            assert cp <= 100.0


class TestPoker:

    def test_rank_hand_pair(self):
        from casino.games.poker import _rank_hand
        hand = ["2♠", "2♥", "5♦", "7♣", "9♠"]
        rank_val, rank_name = _rank_hand(hand)
        assert rank_val == 1
        assert rank_name == "Пара"

    def test_rank_hand_three_of_a_kind(self):
        from casino.games.poker import _rank_hand
        hand = ["K♠", "K♥", "K♦", "3♣", "7♠"]
        rank_val, rank_name = _rank_hand(hand)
        assert rank_val == 3
        assert rank_name == "Тройка"

    def test_rank_hand_four_of_a_kind(self):
        from casino.games.poker import _rank_hand
        hand = ["A♠", "A♥", "A♦", "A♣", "2♠"]
        rank_val, rank_name = _rank_hand(hand)
        assert rank_val == 7
        assert rank_name == "Каре"
