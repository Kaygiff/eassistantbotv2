"""
api/routes/notifications.py — API рассылок через EAdmin.
"""

from __future__ import annotations
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api.auth import require_admin
from infra.db.supabase import get_supabase_admin

router = APIRouter(prefix="/notifications", tags=["notifications"])


class BroadcastRequest(BaseModel):
    text: str
    language: Optional[str] = None
    parse_mode: str = "Markdown"
    limit: int = 1000


class SingleNotificationRequest(BaseModel):
    telegram_id: int
    text: str
    parse_mode: str = "Markdown"


@router.post("/broadcast")
async def broadcast(body: BroadcastRequest, _=Depends(require_admin)):
    from infra.queue.tasks import send_broadcast
    send_broadcast.delay(
        text=body.text,
        language=body.language,
        parse_mode=body.parse_mode,
        limit=body.limit,
    )
    return {"ok": True, "queued": True, "language": body.language}


@router.post("/send")
async def send_single(body: SingleNotificationRequest, _=Depends(require_admin)):
    from infra.queue.tasks import send_single_notification
    send_single_notification.delay(
        telegram_id=body.telegram_id,
        text=body.text,
        parse_mode=body.parse_mode,
    )
    return {"ok": True, "telegram_id": body.telegram_id}


@router.get("/history")
async def notification_history(limit: int = 50, _=Depends(require_admin)):
    res = (
        get_supabase_admin()
        .table("audit_log")
        .select("*")
        .eq("action", "broadcast")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return res.data or []
