from __future__ import annotations
from datetime import datetime
from typing import Literal, Optional
from uuid import UUID
from pydantic import BaseModel

GroupRole = Literal["owner", "co_owner", "admin", "moderator", "user"]


class Group(BaseModel):
    id: UUID
    chat_id: int
    title: str
    owner_id: Optional[UUID] = None
    language: str = "ru"
    welcome_message: Optional[str] = None
    warn_threshold: int = 3
    bot_name: Optional[str] = None
    bot_avatar_url: Optional[str] = None
    created_at: datetime


class GroupCreate(BaseModel):
    chat_id: int
    title: str
    owner_id: Optional[UUID] = None
    language: str = "ru"


class GroupMember(BaseModel):
    id: UUID
    group_id: UUID
    user_id: UUID
    role: GroupRole = "user"
    joined_at: datetime


class GroupWarn(BaseModel):
    id: UUID
    group_id: UUID
    user_id: UUID
    issued_by: Optional[UUID] = None
    reason: Optional[str] = None
    created_at: datetime
