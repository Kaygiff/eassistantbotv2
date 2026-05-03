"""
Pydantic модели: pets.
"""

from __future__ import annotations
from datetime import datetime
from typing import Literal, Optional
from uuid import UUID
from pydantic import BaseModel, Field


PetSpecies = Literal["cat", "dog", "rabbit", "hamster", "fox", "dragon"]
PetMood = Literal["happy", "neutral", "sad", "sick"]


class Pet(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    species: PetSpecies
    level: int = 1
    mood: PetMood = "happy"
    hunger: int = Field(default=100, ge=0, le=100)
    energy: int = Field(default=100, ge=0, le=100)
    is_sick: bool = False
    is_dead: bool = False
    born_at: datetime
    last_interaction_at: datetime


class PetCreate(BaseModel):
    user_id: UUID
    name: str
    species: PetSpecies


class PetUpdate(BaseModel):
    mood: Optional[PetMood] = None
    hunger: Optional[int] = Field(default=None, ge=0, le=100)
    energy: Optional[int] = Field(default=None, ge=0, le=100)
    is_sick: Optional[bool] = None
    is_dead: Optional[bool] = None
    level: Optional[int] = None
