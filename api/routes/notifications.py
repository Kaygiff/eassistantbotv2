"""
api/routes/notifications.py — API рассылок через EAdmin.
Позволяет отправлять сообщения всем или конкретным пользователям.
"""

from __future__ import annotations
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api.auth import require_admin
from db.supabase import supabase_admin

router = APIRouter(prefix="/notifications", tags=["notifications"])


class BroadcastRequest(BaseModel):
    text: str
    language: Optional[str] = None        # None = всем, "ru" = только русским
    parse_mode: str = "Markdown"
    limit: int = 1000                      # Максимум за один запрос


class SingleNotificationRequest(BaseModel):
    telegram_id: int
    text: str
    parse_mode: str = "Markdown"


@router.post("/broadcast")
async def broadcast(body: BroadcastRequest, _=require_admin):
    """
    Ставит задачу массовой рассылки в очередь Celery.
    Не блокирует API — рассылка идёт асинхронно.
    """
    from queue.tasks import send_broadcast
    send_broadcast.delay(
        text=body.text,
        language=body.language,
        parse_mode=body.parse_mode,
        limit=body.limit,
    )
    return {"ok": True, "queued": True, "language": body.language}


@router.post("/send")
async def send_single(body: SingleNotificationRequest, _=require_admin):
    """Отправляет сообщение конкретному пользователю по telegram_id."""
    from queue.tasks import send_single_notification
    send_single_notification.delay(
        telegram_id=body.telegram_id,
        text=body.text,
        parse_mode=body.parse_mode,
    )
    return {"ok": True, "telegram_id": body.telegram_id}


@router.get("/history")
async def notification_history(limit: int = 50, _=require_admin):
    """История отправленных рассылок из audit_log."""
    res = (
        supabase_admin
        .table("audit_log")
        .select("*")
        .eq("action", "broadcast")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return res.data or []
