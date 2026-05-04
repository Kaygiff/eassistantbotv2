"""
tests/test_notifications.py — Тесты отправки уведомлений и планировщика.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestSender:

    @pytest.mark.asyncio
    async def test_send_message_success(self, mocker):
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_resp = MagicMock()
        mock_resp.is_success = True
        mock_client.post = AsyncMock(return_value=mock_resp)
        mocker.patch("notifications.sender.httpx.AsyncClient", return_value=mock_client)

        from infra.notifications.sender import send_message_async
        result = await send_message_async(123456, "Привет!")
        assert result is True

    @pytest.mark.asyncio
    async def test_send_message_failure(self, mocker):
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(side_effect=Exception("Connection error"))
        mocker.patch("notifications.sender.httpx.AsyncClient", return_value=mock_client)

        from infra.notifications.sender import send_message_async
        result = await send_message_async(123456, "Привет!")
        assert result is False

    @pytest.mark.asyncio
    async def test_notify_user_by_uuid(self, mock_supabase, mocker):
        mock_supabase.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = {
            "telegram_id": 987654321
        }
        mock_send = mocker.patch(
            "notifications.sender.send_message_async",
            new_callable=AsyncMock,
            return_value=True,
        )
        from infra.notifications.sender import notify_user
        result = await notify_user("user-uuid-123", "Тест")
        assert result is True
        mock_send.assert_called_once_with(987654321, "Тест", "Markdown")

    @pytest.mark.asyncio
    async def test_notify_user_not_found(self, mock_supabase):
        mock_supabase.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = None
        from infra.notifications.sender import notify_user
        result = await notify_user("nonexistent", "Тест")
        assert result is False


class TestScheduler:

    def test_schedule_reminder_calls_celery(self, mocker):
        from datetime import datetime, timezone, timedelta
        mock_task = mocker.patch("notifications.scheduler.send_reminder")
        mock_task.apply_async = MagicMock()
        run_at = datetime.now(timezone.utc) + timedelta(hours=1)

        from infra.notifications.scheduler import schedule_reminder
        schedule_reminder("task-uuid-123", run_at)

        mock_task.apply_async.assert_called_once()
        assert mock_task.apply_async.call_args[1]["eta"] == run_at

    def test_schedule_broadcast_immediate(self, mocker):
        mock_task = mocker.patch("notifications.scheduler.send_broadcast")
        mock_task.delay = MagicMock()

        from infra.notifications.scheduler import schedule_broadcast
        schedule_broadcast("Всем привет!", language="ru")
        mock_task.delay.assert_called_once_with(text="Всем привет!", language="ru")

    def test_schedule_broadcast_delayed(self, mocker):
        from datetime import datetime, timezone, timedelta
        mock_task = mocker.patch("notifications.scheduler.send_broadcast")
        mock_task.apply_async = MagicMock()
        run_at = datetime.now(timezone.utc) + timedelta(hours=2)

        from infra.notifications.scheduler import schedule_broadcast
        schedule_broadcast("Отложенное!", language="en", run_at=run_at)
        mock_task.apply_async.assert_called_once()


class TestCeleryTasks:

    def test_send_single_notification(self, mocker):
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.is_success = True
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=None)
        mock_client.post = MagicMock(return_value=mock_resp)
        mocker.patch("queue.tasks.httpx.Client", return_value=mock_client)

        from infra.queue.tasks import send_single_notification
        send_single_notification(123456789, "Тест!", "Markdown")

        mock_client.post.assert_called_once()
        assert mock_client.post.call_args[1]["json"]["chat_id"] == 123456789
