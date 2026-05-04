"""
Pydantic модели: actions_log.
"""

from __future__ import annotations
from datetime import datetime
from typing import Literal
from uuid import UUID
from pydantic import BaseModel


ActionCategory = Literal["emotional", "friendly", "aggressive", "nsfw", "profane", "gift"]


class ActionLog(BaseModel):
    id: UUID
    initiator_id: UUID
    target_id: UUID
    action_type: str
    category: ActionCategory
    created_at: datetime


class ActionCreate(BaseModel):
    initiator_id: UUID
    target_id: UUID
    action_type: str
    category: ActionCategory
