"""
api/routes/groups.py — API управления группами через EAdmin.
"""

from __future__ import annotations
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from api.auth import require_admin
from db.supabase import supabase_admin
from models.groups import Group

router = APIRouter(prefix="/groups", tags=["groups"])


@router.get("/", response_model=list[Group])
async def list_groups(
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    search: Optional[str] = None,
    _=require_admin,
):
    """Список всех зарегистрированных групп."""
    query = supabase_admin.table("groups").select("*").order("created_at", desc=True)
    if search:
        query = query.ilike("title", f"%{search}%")
    res = query.range(offset, offset + limit - 1).execute()
    return [Group(**g) for g in (res.data or [])]


@router.get("/{group_id}", response_model=Group)
async def get_group(group_id: UUID, _=require_admin):
    res = supabase_admin.table("groups").select("*").eq("id", str(group_id)).maybe_single().execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Group not found")
    return Group(**res.data)


@router.get("/{group_id}/members")
async def get_members(group_id: UUID, _=require_admin):
    res = (
        supabase_admin
        .table("group_members")
        .select("*, users(username, first_name)")
        .eq("group_id", str(group_id))
        .execute()
    )
    return res.data or []


@router.get("/{group_id}/warns")
async def get_warns(group_id: UUID, _=require_admin):
    res = (
        supabase_admin
        .table("group_warns")
        .select("*, users(username, first_name)")
        .eq("group_id", str(group_id))
        .order("created_at", desc=True)
        .execute()
    )
    return res.data or []


class GroupSettingsUpdate(BaseModel):
    warn_threshold: Optional[int] = None
    welcome_message: Optional[str] = None
    language: Optional[str] = None
    bot_name: Optional[str] = None


@router.patch("/{group_id}/settings")
async def update_group_settings(group_id: UUID, body: GroupSettingsUpdate, _=require_admin):
    update_data = {k: v for k, v in body.dict().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")
    supabase_admin.table("groups").update(update_data).eq("id", str(group_id)).execute()
    return {"ok": True}


@router.delete("/{group_id}/warns/{user_id}")
async def clear_user_warns(group_id: UUID, user_id: UUID, _=require_admin):
    """Очищает все варны пользователя в группе."""
    from safety.group_moderation import clear_warns
    await clear_warns(str(group_id), str(user_id))
    return {"ok": True}
