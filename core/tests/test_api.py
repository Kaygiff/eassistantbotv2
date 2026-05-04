"""
tests/test_api.py — Тесты REST API эндпоинтов.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch, AsyncMock


@pytest.fixture
def api_client(mocker):
    """Создаёт тестовый FastAPI клиент с моками."""
    # Мокируем Supabase и Redis до импорта app
    mocker.patch("db.supabase.get_supabase_client", return_value=MagicMock())
    mocker.patch("db.supabase.get_supabase_admin", return_value=MagicMock())
    mocker.patch("db.redis.get_redis_pool", return_value=MagicMock())

    from api.app import app
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def admin_token():
    """JWT токен администратора для тестов."""
    from api.auth import create_admin_token
    return create_admin_token("admin-uuid-123")


class TestHealthEndpoint:

    def test_health_returns_200(self, api_client, mocker):
        mocker.patch(
            "monitoring.health.get_health",
            new_callable=AsyncMock,
            return_value={"status": "healthy", "services": {}, "timestamp": 1234567890.0},
        )
        response = api_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data

    def test_root_returns_service_info(self, api_client):
        response = api_client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "E'assistant" in data.get("service", "")


class TestUsersAPI:

    def test_list_users_requires_auth(self, api_client):
        response = api_client.get("/api/v1/users/")
        assert response.status_code == 403

    def test_list_users_with_valid_token(self, api_client, admin_token, mocker):
        mocker.patch(
            "api.routes.users.supabase_admin",
            **{
                "table.return_value.select.return_value.order.return_value.range.return_value.execute.return_value.data": []
            }
        )
        response = api_client.get(
            "/api/v1/users/",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)


class TestWebhookEndpoint:

    def test_webhook_rejects_invalid_secret(self, api_client):
        import os
        with patch.dict(os.environ, {"TELEGRAM_WEBHOOK_SECRET": "correct-secret"}):
            response = api_client.post(
                "/webhook",
                json={"update_id": 1},
                headers={"X-Telegram-Bot-Api-Secret-Token": "wrong-secret"},
            )
            assert response.status_code == 403

    def test_webhook_accepts_valid_secret(self, api_client, mocker):
        import os
        mocker.patch("bot.webhook.get_bot_and_dp", return_value=(MagicMock(), AsyncMock()))
        with patch.dict(os.environ, {"TELEGRAM_WEBHOOK_SECRET": "test-secret"}):
            response = api_client.post(
                "/webhook",
                json={"update_id": 1, "message": {}},
                headers={"X-Telegram-Bot-Api-Secret-Token": "test-secret"},
            )
            assert response.status_code == 200
