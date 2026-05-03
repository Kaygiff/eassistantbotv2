"""
tests/test_virtual_world.py — Тесты виртуального мира:
отношения, семья, действия, события, чёрный список.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4


class TestRelationships:

    @pytest.mark.asyncio
    async def test_get_status_no_relationship(self, mock_supabase):
        mock_supabase.table.return_value.select.return_value.or_.return_value.maybe_single.return_value.execute.return_value.data = None

        from virtual_world.relationships.service import get_relationship_status
        result = await get_relationship_status(str(uuid4()), "ru")
        assert "свободен" in result.lower()

    @pytest.mark.asyncio
    async def test_get_status_dating(self, mock_supabase):
        user_a = str(uuid4())
        mock_supabase.table.return_value.select.return_value.or_.return_value.maybe_single.return_value.execute.return_value.data = {
            "id": str(uuid4()), "user_a_id": user_a, "user_b_id": str(uuid4()),
            "status": "dating", "started_at": "2025-01-01T00:00:00+00:00", "married_at": None,
        }
        mock_supabase.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = {
            "first_name": "Аня", "username": "anya",
        }
        from virtual_world.relationships.service import get_relationship_status
        result = await get_relationship_status(user_a, "ru")
        assert "встречаетесь" in result

    @pytest.mark.asyncio
    async def test_breakup_no_relationship(self, mock_supabase):
        mock_supabase.table.return_value.select.return_value.or_.return_value.maybe_single.return_value.execute.return_value.data = None
        from virtual_world.relationships.service import breakup
        result = await breakup(str(uuid4()), "ru")
        assert "нет" in result.lower()

    def test_ordered_pair_consistency(self):
        from virtual_world.relationships.service import _ordered_pair
        a, b = "user-aaa", "user-zzz"
        assert _ordered_pair(a, b) == _ordered_pair(b, a)

    @pytest.mark.asyncio
    async def test_divorce_not_married(self, mock_supabase):
        mock_supabase.table.return_value.select.return_value.or_.return_value.maybe_single.return_value.execute.return_value.data = None
        from virtual_world.relationships.service import divorce
        result = await divorce(str(uuid4()), "ru")
        assert "брак" in result.lower()


class TestFamilyRelations:

    @pytest.mark.asyncio
    async def test_get_family_tree_empty(self, mock_supabase):
        mock_supabase.table.return_value.select.return_value.or_.return_value.eq.return_value.execute.return_value.data = []
        from virtual_world.family.service import get_family_tree
        result = await get_family_tree(str(uuid4()), "ru")
        assert "нет" in result.lower() or "пока" in result.lower()

    def test_role_pairs_completeness(self):
        from virtual_world.family.service import ROLE_PAIRS
        assert "родитель" in ROLE_PAIRS
        assert "брат" in ROLE_PAIRS
        assert "дедушка" in ROLE_PAIRS

    def test_detect_role_from_text(self):
        from virtual_world.family.service import _detect_role
        assert _detect_role("стать братом @user") == "брат"
        assert _detect_role("хочу стать родителем @user") == "родитель"
        assert _detect_role("hello world") is None


class TestActions:

    def test_detect_hug(self):
        from virtual_world.actions.service import _detect_action
        result = _detect_action("обними @user")
        assert result is not None
        _, data = result
        assert data["category"] == "friendly"

    def test_detect_kiss(self):
        from virtual_world.actions.service import _detect_action
        result = _detect_action("поцелуй @user")
        assert result is not None
        _, data = result
        assert data["category"] == "emotional"

    def test_detect_aggressive(self):
        from virtual_world.actions.service import _detect_action
        result = _detect_action("ударь @user")
        assert result is not None
        _, data = result
        assert data["category"] == "aggressive"

    def test_detect_unknown_returns_none(self):
        from virtual_world.actions.service import _detect_action
        assert _detect_action("привет как дела") is None

    @pytest.mark.asyncio
    async def test_cooldown_blocks_repeat(self, fake_redis):
        with patch("virtual_world.actions.service.get_redis", return_value=fake_redis):
            from virtual_world.actions.service import _check_cooldown, _set_cooldown
            user_a, user_b = str(uuid4()), str(uuid4())

            assert await _check_cooldown(user_a, user_b, "обнять") is False
            await _set_cooldown(user_a, user_b, "обнять")
            assert await _check_cooldown(user_a, user_b, "обнять") is True

    @pytest.mark.asyncio
    async def test_different_actions_independent(self, fake_redis):
        with patch("virtual_world.actions.service.get_redis", return_value=fake_redis):
            from virtual_world.actions.service import _check_cooldown, _set_cooldown
            user_a, user_b = str(uuid4()), str(uuid4())
            await _set_cooldown(user_a, user_b, "обнять")
            assert await _check_cooldown(user_a, user_b, "поцеловать") is False


class TestEvents:

    @pytest.mark.asyncio
    async def test_events_list_empty(self, mock_supabase):
        mock_supabase.table.return_value.select.return_value.eq.return_value.gte.return_value.order.return_value.limit.return_value.execute.return_value.data = []
        from virtual_world.events.service import get_events_list
        result = await get_events_list(123456, "ru")
        assert "нет" in result.lower()

    @pytest.mark.asyncio
    async def test_events_list_with_data(self, mock_supabase):
        mock_supabase.table.return_value.select.return_value.eq.return_value.gte.return_value.order.return_value.limit.return_value.execute.return_value.data = [{
            "id": str(uuid4()), "title": "Вечеринка",
            "event_at": "2026-12-31T20:00:00+00:00", "creator_id": str(uuid4()),
            "users!creator_id": {"first_name": "Иван", "username": "ivan"},
        }]
        from virtual_world.events.service import get_events_list
        result = await get_events_list(123456, "ru")
        assert "Вечеринка" in result


class TestBlacklist:

    @pytest.mark.asyncio
    async def test_add_to_blacklist_success(self, mock_supabase):
        mock_supabase.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = {
            "id": str(uuid4()), "first_name": "Вася", "username": "vasya",
        }
        mock_supabase.table.return_value.upsert.return_value.execute = MagicMock()

        from virtual_world.blacklist.service import add_to_blacklist
        result = await add_to_blacklist(str(uuid4()), "vasya", "ru")
        assert "Вася" in result

    @pytest.mark.asyncio
    async def test_add_user_not_found(self, mock_supabase):
        mock_supabase.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = None
        from virtual_world.blacklist.service import add_to_blacklist
        result = await add_to_blacklist(str(uuid4()), "ghost", "ru")
        assert "не найден" in result.lower()

    @pytest.mark.asyncio
    async def test_is_blocked_true(self, mock_supabase):
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = {"id": str(uuid4())}
        from virtual_world.blacklist.service import is_blocked
        assert await is_blocked(str(uuid4()), str(uuid4())) is True

    @pytest.mark.asyncio
    async def test_is_blocked_false(self, mock_supabase):
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = None
        from virtual_world.blacklist.service import is_blocked
        assert await is_blocked(str(uuid4()), str(uuid4())) is False
