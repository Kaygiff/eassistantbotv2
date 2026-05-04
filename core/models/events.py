from __future__ import annotations
from datetime import datetime
from typing import Literal, Optional
from uuid import UUID
from pydantic import BaseModel

EventType = Literal["open", "invite"]
ParticipantStatus = Literal["accepted", "declined", "pending"]


class Event(BaseModel):
    id: UUID
    creator_id: UUID
    chat_id: int
    title: str
    description: Optional[str] = None
    event_at: datetime
    type: EventType = "open"
    created_at: datetime


class EventCreate(BaseModel):
    creator_id: UUID
    chat_id: int
    title: str
    description: Optional[str] = None
    event_at: datetime
    type: EventType = "open"


class EventParticipant(BaseModel):
    event_id: UUID
    user_id: UUID
    status: ParticipantStatus = "pending"
    joined_at: Optional[datetime] = None
