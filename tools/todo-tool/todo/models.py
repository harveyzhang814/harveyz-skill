from pydantic import BaseModel
from typing import Optional


class TaskCreate(BaseModel):
    title: str
    project: str
    priority: str = "P2"


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None


class Task(BaseModel):
    id: int
    title: str
    project: str
    priority: str
    status: str
    created_at: str
