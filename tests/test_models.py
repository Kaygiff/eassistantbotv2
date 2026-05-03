"""
tests/test_models.py — Тесты валидации Pydantic моделей.
"""

import pytest
from datetime import datetime, timezone
from uuid import uuid4


class TestUserModel:

    def test_valid_user(self):
        from models.user import User
        user = User(
            id=uuid4(),
            telegram_id=123456,
            language="ru",
            assistant_name="Алекс",
            is_banned=False,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        assert user.telegram_id == 123456
        assert user.language == "ru"

    def test_user_create(self):
        from models.user import UserCreate
        uc = UserCreate(
            telegram_id=789,
            language="en",
            assistant_name="Alex",
        )
        assert uc.telegram_id == 789


class TestPetModel:

    def test_valid_pet(self):
        from models.pets import Pet
        pet = Pet(
            id=uuid4(),
            user_id=uuid4(),
            name="Барсик",
            species="cat",
            hunger=80,
            energy=90,
            born_at=datetime.now(timezone.utc),
            last_interaction_at=datetime.now(timezone.utc),
        )
        assert pet.name == "Барсик"
        assert pet.species == "cat"
        assert pet.hunger == 80

    def test_pet_hunger_bounds(self):
        from models.pets import PetUpdate
        import pydantic
        with pytest.raises(pydantic.ValidationError):
            PetUpdate(hunger=150)  # > 100

        with pytest.raises(pydantic.ValidationError):
            PetUpdate(hunger=-1)  # < 0


class TestEcoinTransaction:

    def test_valid_transaction(self):
        from models.economy import EcoinTransactionCreate
        tx = EcoinTransactionCreate(
            user_id=uuid4(),
            type="credit",
            amount=100,
            balance_after=600,
            reason="daily_bonus",
        )
        assert tx.amount == 100
        assert tx.type == "credit"

    def test_invalid_amount(self):
        from models.economy import EcoinTransactionCreate
        import pydantic
        with pytest.raises(pydantic.ValidationError):
            EcoinTransactionCreate(
                user_id=uuid4(),
                type="credit",
                amount=0,  # должно быть > 0
                balance_after=100,
                reason="daily_bonus",
            )


class TestTaskModel:

    def test_valid_task(self):
        from models.tasks import TaskCreate
        task = TaskCreate(
            user_id=uuid4(),
            type="todo",
            title="Купить молоко",
            priority="high",
        )
        assert task.title == "Купить молоко"
        assert task.priority == "high"

    def test_invalid_priority(self):
        from models.tasks import TaskCreate
        import pydantic
        with pytest.raises(pydantic.ValidationError):
            TaskCreate(
                user_id=uuid4(),
                type="todo",
                title="Test",
                priority="critical",  # не валидное значение
            )
