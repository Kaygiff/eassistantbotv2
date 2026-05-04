from __future__ import annotations
from datetime import datetime
from typing import Any, Literal, Optional
from uuid import UUID
from pydantic import BaseModel

GameMode = Literal["solo", "multiplayer"]
GameStatus = Literal["active", "finished", "abandoned"]
GameResult = Literal["win", "loss", "draw"]
GameOutcome = Literal["win", "loss", "push"]
Difficulty = Literal["easy", "medium", "hard"]


class GameSession(BaseModel):
    id: UUID
    user_id: UUID
    opponent_id: Optional[UUID] = None
    game_type: str
    mode: GameMode = "solo"
    status: GameStatus = "active"
    result: Optional[GameResult] = None
    score: Optional[dict[str, Any]] = None
    room_code: Optional[str] = None
    created_at: datetime
    finished_at: Optional[datetime] = None


class GameLeaderboard(BaseModel):
    id: UUID
    user_id: UUID
    game_type: str
    wins: int = 0
    losses: int = 0
    draws: int = 0
    best_score: int = 0
    updated_at: datetime


class CasinoRound(BaseModel):
    id: UUID
    user_id: UUID
    opponent_id: Optional[UUID] = None
    game_type: str
    mode: GameMode = "solo"
    amount: int
    payout: int = 0
    house_fee: int = 0
    result: Optional[dict[str, Any]] = None
    outcome: Optional[GameOutcome] = None
    seed_hash: Optional[str] = None
    created_at: datetime


class CasinoRoundCreate(BaseModel):
    user_id: UUID
    game_type: str
    amount: int
    mode: GameMode = "solo"
    opponent_id: Optional[UUID] = None
