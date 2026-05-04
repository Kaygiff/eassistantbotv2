"""
api/routes/users.py — REST API для пользователей.
Используется EAdmin для просмотра и управления профилями.
"""

from __future__ import annotations
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from db.supabase import supabase_admin
from models.user import User
from api.auth import require_admin

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/", response_model=list[User])
async def list_users(
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    search: Optional[str] = None,
    language: Optional[str] = None,
    is_banned: Optional[bool] = None,
    _=Depends(require_admin),
):
    """Список пользователей с фильтрацией."""
    query = supabase_admin.table("users").select("*").order("created_at", desc=True)

    if search:
        query = query.ilike("username", f"%{search}%")
    if language:
        query = query.eq("language", language)
    if is_banned is not None:
        query = query.eq("is_banned", is_banned)

    res = query.range(offset, offset + limit - 1).execute()
    return [User(**u) for u in (res.data or [])]


@router.get("/{user_id}", response_model=User)
async def get_user(user_id: UUID, _=Depends(require_admin)):
    """Получить пользователя по UUID."""
    res = supabase_admin.table("users").select("*").eq("id", str(user_id)).maybe_single().execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="User not found")
    return User(**res.data)


class BanRequest(BaseModel):
    reason: Optional[str] = None
    ban_until: Optional[str] = None


@router.post("/{user_id}/ban")
async def ban_user(user_id: UUID, body: BanRequest, _=Depends(require_admin)):
    """Заблокировать пользователя."""
    from safety.user_ban import ban_user as do_ban
    from datetime import datetime
    ban_until = datetime.fromisoformat(body.ban_until) if body.ban_until else None
    await do_ban(str(user_id), reason=body.reason, ban_until=ban_until, banned_by="admin")
    return {"ok": True}


@router.post("/{user_id}/unban")
async def unban_user(user_id: UUID, _=Depends(require_admin)):
    """Разблокировать пользователя."""
    from safety.user_ban import lift_ban
    await lift_ban(str(user_id))
    return {"ok": True}


@router.get("/{user_id}/wallet")
async def get_wallet(user_id: UUID, _=Depends(require_admin)):
    """Получить кошелёк пользователя."""
    res = supabase_admin.table("ecoin_wallets").select("*").eq("user_id", str(user_id)).maybe_single().execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Wallet not found")
    return res.data


@router.get("/{user_id}/transactions")
async def get_transactions(
    user_id: UUID,
    limit: int = Query(50, le=200),
    _=Depends(require_admin),
):
    """История транзакций пользователя."""
    res = (
        supabase_admin.table("ecoin_transactions")
        .select("*")
        .eq("user_id", str(user_id))
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return res.data or []
