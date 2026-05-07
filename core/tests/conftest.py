"""
tests/conftest.py — Общие фикстуры для всех тестов.
Использует fakeredis и мок Supabase для изоляции.
"""

from __future__ import annotations
import asyncio
import os
import pytest
import fakeredis.aioredis

# Устанавливаем тестовые env-переменные до импорта модулей
os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "test-key")
os.environ.setdefault("SUPABASE_SERVICE_KEY", "test-service-key")
os.environ.setdefault("OPENAI_API_KEY", "sk-test")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "123456:test-token")
os.environ.setdefault("APP_ENV", "test")


@pytest.fixture(scope="session")
def event_loop():
    """Единый event loop для всей сессии тестов."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def fake_redis():
    """Фейковый Redis для тестов (не требует реального Redis)."""
    redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    yield redis
    await redis.flushall()


@pytest.fixture
def mock_supabase(mocker):
    """Мок Supabase клиента."""
    mock = mocker.MagicMock()
    mocker.patch("db.supabase.supabase_admin", mock)
    mocker.patch("db.supabase.supabase", mock)
    return mock


@pytest.fixture
def mock_bot(mocker):
    """Мок Telegram бота."""
    bot = mocker.AsyncMock()
    bot.send_message = mocker.AsyncMock(return_value=True)
    bot.send_chat_action = mocker.AsyncMock(return_value=True)
    bot.send_audio = mocker.AsyncMock(return_value=True)
    bot.send_photo = mocker.AsyncMock(return_value=True)
    return bot


@pytest.fixture
def sample_user():
    """Тестовый пользователь."""
    from core.models.user import User
    from datetime import datetime, timezone
    from uuid import uuid4
    return User(
        id=uuid4(),
        telegram_id=123456789,
        username="test_user",
        first_name="Test",
        language="ru",
        assistant_name="Алекс",
        is_banned=False,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def sample_context(sample_user):
    """Тестовый BrainContext."""
    from bot.brain.context import BrainContext
    ctx = BrainContext(
        telegram_id=sample_user.telegram_id,
        chat_id=sample_user.telegram_id,
        message_id=1,
        text="",
        is_group=False,
    )
    ctx.user = sample_user
    ctx.language = "ru"
    return ctx
