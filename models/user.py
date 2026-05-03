"""
Pydantic модели: users, ecoin_wallets, daily_bonuses, referrals.
"""

from __future__ import annotations
from datetime import date, datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field


class User(BaseModel):
    id: UUID
    telegram_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    language: str = "ru"
    assistant_name: str = "Ассистент"
    nickname: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    birthday: Optional[date] = None
    timezone: str = "UTC"
    is_banned: bool = False
    ban_until: Optional[datetime] = None
    ban_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class UserCreate(BaseModel):
    telegram_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    language: str = "ru"
    assistant_name: str


class UserUpdate(BaseModel):
    language: Optional[str] = None
    assistant_name: Optional[str] = None
    nickname: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    birthday: Optional[date] = None
    timezone: Optional[str] = None


class EcoinWallet(BaseModel):
    user_id: UUID
    balance: int = Field(ge=0)
    updated_at: datetime


class DailyBonus(BaseModel):
    user_id: UUID
    streak_days: int = 0
    last_bonus_at: Optional[datetime] = None
    total_bonuses_earned: int = 0


class Referral(BaseModel):
    id: UUID
    referrer_id: UUID
    referee_id: UUID
    ref_code: str
    bonus_paid: bool = False
    total_commission_earned: int = 0
    created_at: datetime
