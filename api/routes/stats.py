"""
api/routes/stats.py — Аналитика и статистика для EAdmin.
"""

from fastapi import APIRouter, Depends, Query
from api.auth import require_admin
from db.supabase import supabase_admin

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/users/growth")
async def users_growth(days: int = Query(30, le=365), _=Depends(require_admin)):
    """Рост пользователей по дням."""
    from datetime import datetime, timedelta, timezone
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    res = (
        supabase_admin.table("users")
        .select("created_at")
        .gte("created_at", since)
        .order("created_at")
        .execute()
    )
    return res.data or []


@router.get("/economy/volume")
async def economy_volume(days: int = Query(7, le=90), _=Depends(require_admin)):
    """Объём транзакций Ecoins."""
    from datetime import datetime, timedelta, timezone
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    res = (
        supabase_admin.table("ecoin_transactions")
        .select("type, amount, reason, created_at")
        .gte("created_at", since)
        .execute()
    )
    return res.data or []


@router.get("/casino/rounds")
async def casino_rounds(days: int = Query(7, le=90), _=Depends(require_admin)):
    """Статистика раундов казино."""
    from datetime import datetime, timedelta, timezone
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    res = (
        supabase_admin.table("casino_rounds")
        .select("game_type, outcome, amount, payout, house_fee, created_at")
        .gte("created_at", since)
        .execute()
    )
    return res.data or []


@router.get("/languages")
async def language_distribution(_=Depends(require_admin)):
    """Распределение пользователей по языкам."""
    res = supabase_admin.table("users").select("language").execute()
    from collections import Counter
    counts = Counter(u["language"] for u in (res.data or []))
    return dict(counts)
