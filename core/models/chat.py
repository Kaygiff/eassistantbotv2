from __future__ import annotations
from datetime import datetime
from typing import Literal, Optional
from uuid import UUID
from pydantic import BaseModel

MessageRole = Literal["user", "assistant", "system"]


class ChatMessage(BaseModel):
    id: UUID
    user_id: UUID
    role: MessageRole
    content: str
    model_used: Optional[str] = None
    tokens_used: Optional[int] = None
    response_ms: Optional[int] = None
    created_at: datetime


class ChatMessageCreate(BaseModel):
    user_id: UUID
    role: MessageRole
    content: str
    model_used: Optional[str] = None
    tokens_used: Optional[int] = None
    response_ms: Optional[int] = None


class MusicCache(BaseModel):
    id: UUID
    youtube_id: str
    title: Optional[str] = None
    artist: Optional[str] = None
    storage_url: str
    lyrics_url: Optional[str] = None
    created_at: datetime
