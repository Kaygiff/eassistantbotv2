from __future__ import annotations
from datetime import datetime
from typing import Literal, Optional
from uuid import UUID
from pydantic import BaseModel

TaskType = Literal["todo", "reminder"]
TaskPriority = Literal["high", "medium", "low"]
TaskStatus = Literal["pending", "done"]
RepeatRule = Literal["once", "daily", "weekly", "monthly"]


class Task(BaseModel):
    id: UUID
    user_id: UUID
    group_id: Optional[UUID] = None
    type: TaskType
    title: str
    priority: TaskPriority = "medium"
    due_at: Optional[datetime] = None
    repeat_rule: Optional[RepeatRule] = None
    status: TaskStatus = "pending"
    reminder_sent: bool = False
    created_at: datetime
    updated_at: datetime


class TaskCreate(BaseModel):
    user_id: UUID
    group_id: Optional[UUID] = None
    type: TaskType
    title: str
    priority: TaskPriority = "medium"
    due_at: Optional[datetime] = None
    repeat_rule: Optional[RepeatRule] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    priority: Optional[TaskPriority] = None
    due_at: Optional[datetime] = None
    status: Optional[TaskStatus] = None
