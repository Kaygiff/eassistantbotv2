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
    last_name: Optional[str] = None
    language: str = "ru"
    locale: Optional[str] = None
    assistant_name: str = "Ассистент"
    nickname: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    birthday: Optional[date] = None
    timezone: str = "UTC"
    is_premium: bool = False
    is_admin: bool = False
    is_banned: bool = False
    ban_until: Optional[datetime] = None
    ban_reason: Optional[str] = None
    messages_count: int = 0
    xp: int = 0
    level: int = 1
    rep: int = 0
    referral_code: Optional[str] = None
    last_seen_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    @property
    def display_name(self) -> str:
        """Красивое имя для отображения в профиле и сообщениях."""
        if self.nickname:
            return self.nickname
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        if self.first_name:
            return self.first_name
        if self.username:
            return f"@{self.username}"
        return f"User#{self.telegram_id}"

    @property
    def mention(self) -> str:
        """@username или имя для упоминания."""
        if self.username:
            return f"@{self.username}"
        return self.display_name

    @property
    def full_name(self) -> str:
        """Полное имя из Telegram (first + last)."""
        parts = [self.first_name, self.last_name]
        return " ".join(p for p in parts if p) or self.mention


class UserCreate(BaseModel):
    telegram_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    language: str = "ru"
    locale: Optional[str] = None
    is_premium: bool = False
    assistant_name: str = "Ассистент"


class UserUpdate(BaseModel):
    language: Optional[str] = None
    locale: Optional[str] = None
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
