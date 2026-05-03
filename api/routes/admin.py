"""
api/routes/admin.py — Административные действия через EAdmin.
"""

from fastapi import APIRouter
from api.auth import require_admin
from db.supabase import supabase_admin

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/dashboard")
async def dashboard(_=require_admin):
    """Общая статистика для главного дашборда EAdmin."""
    users_count = supabase_admin.table("users").select("id", count="exact").execute().count or 0
    banned_count = supabase_admin.table("users").select("id", count="exact").eq("is_banned", True).execute().count or 0
    groups_count = supabase_admin.table("groups").select("id", count="exact").execute().count or 0
    tx_count = supabase_admin.table("ecoin_transactions").select("id", count="exact").execute().count or 0

    return {
        "users_total": users_count,
        "users_banned": banned_count,
        "groups_total": groups_count,
        "transactions_total": tx_count,
    }
