"""
api/routes/flags.py — Feature Flags API для EAdmin.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from api.auth import require_admin
from api.feature_flags.flags import set_flag, invalidate_flag_cache
from infra.db.supabase import get_supabase_admin

router = APIRouter(prefix="/flags", tags=["flags"])


@router.get("/")
async def list_flags(_=Depends(require_admin)):
    res = get_supabase_admin().table("feature_flags").select("*").execute()
    return res.data or []


class FlagUpdate(BaseModel):
    enabled: bool


@router.put("/{flag_name}")
async def update_flag(flag_name: str, body: FlagUpdate, _=Depends(require_admin)):
    await set_flag(flag_name, body.enabled)
    return {"ok": True, "flag": flag_name, "enabled": body.enabled}


@router.delete("/{flag_name}/cache")
async def clear_flag_cache(flag_name: str, _=Depends(require_admin)):
    await invalidate_flag_cache(flag_name)
    return {"ok": True}
