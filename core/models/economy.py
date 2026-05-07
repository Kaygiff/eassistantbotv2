from __future__ import annotations
from datetime import datetime
from typing import Literal, Optional
from uuid import UUID
from pydantic import BaseModel, Field

TransactionType = Literal["credit", "debit"]
TransactionReason = Literal[
    "daily_bonus", "referral_signup", "referral_commission",
    "game_win", "casino_bet", "transfer_in", "transfer_out",
    "pet_heal", "admin"
]


class EcoinTransaction(BaseModel):
    id: UUID
    user_id: UUID
    type: TransactionType
    amount: int = Field(gt=0)
    balance_after: int = Field(ge=0)
    reason: TransactionReason
    related_id: Optional[UUID] = None
    created_at: datetime


class EcoinTransactionCreate(BaseModel):
    user_id: UUID
    type: TransactionType
    amount: int = Field(gt=0)
    balance_after: int = Field(ge=0)
    reason: TransactionReason
    related_id: Optional[UUID] = None
