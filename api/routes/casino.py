"""
api/routes/casino.py — API статистики казино для EAdmin.
"""

from __future__ import annotations
from typing import Optional

from fastapi import APIRouter, Depends, Query

from api.auth import require_admin
from infra.db.supabase import get_supabase_admin

router = APIRouter(prefix="/casino", tags=["casino"])


@router.get("/stats")
async def casino_stats(_=Depends(require_admin)):
    """Общая статистика казино."""
    rounds = get_supabase_admin().table("casino_rounds").select("outcome, amount, payout, house_fee, game_type").execute()
    data = rounds.data or []

    total_bet = sum(r["amount"] for r in data)
    total_payout = sum(r["payout"] for r in data)
    total_house = sum(r["house_fee"] for r in data)
    wins = sum(1 for r in data if r["outcome"] == "win")
    losses = sum(1 for r in data if r["outcome"] == "loss")

    by_game: dict = {}
    for r in data:
        g = r["game_type"]
        if g not in by_game:
            by_game[g] = {"rounds": 0, "bet": 0, "payout": 0, "house": 0}
        by_game[g]["rounds"] += 1
        by_game[g]["bet"] += r["amount"]
        by_game[g]["payout"] += r["payout"]
        by_game[g]["house"] += r["house_fee"]

    return {
        "total_rounds": len(data),
        "total_bet": total_bet,
        "total_payout": total_payout,
        "total_house_fee": total_house,
        "wins": wins,
        "losses": losses,
        "by_game": by_game,
    }


@router.get("/rounds")
async def list_rounds(
    limit: int = Query(100, le=500),
    game_type: Optional[str] = None,
    outcome: Optional[str] = None,
    _=Depends(require_admin),
):
    """Список раундов казино с фильтрацией."""
    query = (
        get_supabase_admin()
        .table("casino_rounds")
        .select("*")
        .order("created_at", desc=True)
        .limit(limit)
    )
    if game_type:
        query = query.eq("game_type", game_type)
    if outcome:
        query = query.eq("outcome", outcome)
    res = query.execute()
    return res.data or []


@router.get("/leaderboard")
async def casino_leaderboard(
    game_type: Optional[str] = None,
    limit: int = Query(20, le=100),
    _=Depends(require_admin),
):
    """Таблица лидеров казино."""
    query = (
        get_supabase_admin()
        .table("game_leaderboard")
        .select("*, users(username, first_name)")
        .order("wins", desc=True)
        .limit(limit)
    )
    if game_type:
        query = query.eq("game_type", game_type)
    res = query.execute()
    return res.data or []
