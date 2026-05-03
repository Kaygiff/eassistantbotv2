"""
Pydantic модели: relationships, family_relations, blacklist, virtual_world_profiles.
"""

from __future__ import annotations
from datetime import datetime
from typing import Literal, Optional
from uuid import UUID
from pydantic import BaseModel


RelationshipStatus = Literal["dating", "married"]
FamilyStatus = Literal["pending", "active"]


class VirtualWorldProfile(BaseModel):
    id: UUID
    user_id: UUID
    nickname: Optional[str] = None
    status: Optional[str] = None
    bio: Optional[str] = None
    created_at: datetime


class Relationship(BaseModel):
    id: UUID
    user_a_id: UUID
    user_b_id: UUID
    status: RelationshipStatus
    started_at: datetime
    married_at: Optional[datetime] = None


class RelationshipCreate(BaseModel):
    user_a_id: UUID
    user_b_id: UUID
    status: RelationshipStatus


class FamilyRelation(BaseModel):
    id: UUID
    initiator_id: UUID
    target_id: UUID
    initiator_role: str
    target_role: str
    status: FamilyStatus = "pending"
    created_at: datetime


class FamilyRelationCreate(BaseModel):
    initiator_id: UUID
    target_id: UUID
    initiator_role: str
    target_role: str


class BlacklistEntry(BaseModel):
    id: UUID
    blocker_id: UUID
    blocked_id: UUID
    created_at: datetime
