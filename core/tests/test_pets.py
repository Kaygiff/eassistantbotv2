"""
tests/test_pets.py — Тесты системы питомцев.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock


class TestPetDecay:

    @pytest.mark.asyncio
    async def test_decay_reduces_hunger(self, mocker):
        pet = {
            "id": "pet-uuid",
            "user_id": "user-uuid",
            "name": "Барсик",
            "species": "cat",
            "hunger": 80,
            "energy": 70,
            "is_sick": False,
            "is_dead": False,
            "mood": "happy",
        }
        mock_db = mocker.patch("virtual_world.pets.decay.supabase_admin")
        mock_db.table.return_value.update.return_value.eq.return_value.execute = MagicMock()

        from world.virtual_world.pets.decay import process_single_pet
        await process_single_pet(pet)

        # Проверяем что update был вызван
        mock_db.table.return_value.update.assert_called_once()
        call_args = mock_db.table.return_value.update.call_args[0][0]
        assert call_args["hunger"] == 75  # 80 - 5
        assert call_args["energy"] == 67  # 70 - 3

    @pytest.mark.asyncio
    async def test_pet_gets_sick_at_zero_hunger(self, mocker):
        pet = {
            "id": "pet-uuid",
            "user_id": "user-uuid",
            "name": "Барсик",
            "species": "cat",
            "hunger": 3,   # ниже порога decay
            "energy": 50,
            "is_sick": False,
            "is_dead": False,
            "mood": "sad",
        }
        mock_db = mocker.patch("virtual_world.pets.decay.supabase_admin")
        mock_db.table.return_value.update.return_value.eq.return_value.execute = MagicMock()
        mocker.patch("virtual_world.pets.decay.notify_user", new_callable=AsyncMock)

        from world.virtual_world.pets.decay import process_single_pet
        await process_single_pet(pet)

        call_args = mock_db.table.return_value.update.call_args[0][0]
        assert call_args["is_sick"] is True
        assert call_args["mood"] == "sick"

    @pytest.mark.asyncio
    async def test_sick_pet_dies_at_zero(self, mocker):
        pet = {
            "id": "pet-uuid",
            "user_id": "user-uuid",
            "name": "Барсик",
            "species": "cat",
            "hunger": 3,
            "energy": 2,
            "is_sick": True,
            "is_dead": False,
            "mood": "sick",
        }
        mock_db = mocker.patch("virtual_world.pets.decay.supabase_admin")
        mock_db.table.return_value.update.return_value.eq.return_value.execute = MagicMock()
        mocker.patch("virtual_world.pets.decay.notify_user", new_callable=AsyncMock)

        from world.virtual_world.pets.decay import process_single_pet
        await process_single_pet(pet)

        call_args = mock_db.table.return_value.update.call_args[0][0]
        assert call_args["is_dead"] is True


class TestPetService:

    @pytest.mark.asyncio
    async def test_feed_pet_increases_hunger(self, mock_supabase):
        mock_supabase.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = {
            "id": "pet-uuid",
            "user_id": "user-uuid",
            "name": "Барсик",
            "species": "cat",
            "hunger": 60,
            "energy": 80,
            "is_sick": False,
            "is_dead": False,
            "mood": "neutral",
            "level": 1,
        }
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute = MagicMock()

        from world.virtual_world.pets.service import feed_pet
        result = await feed_pet("user-uuid", "ru")
        assert "Барсик" in result
        assert "fed" in result.lower() or "покормлен" in result

    @pytest.mark.asyncio
    async def test_feed_no_pet(self, mock_supabase):
        mock_supabase.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = None

        from world.virtual_world.pets.service import feed_pet
        result = await feed_pet("user-uuid", "ru")
        assert "питомца" in result.lower() or "нет" in result.lower()
