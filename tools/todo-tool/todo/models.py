from pydantic import BaseModel
from typing import Optional


class ProjectCreate(BaseModel):
    repo_name: str
    local_path: Optional[str] = None


class ProjectUpdate(BaseModel):
    repo_name: Optional[str] = None
    local_path: Optional[str] = None


class Project(BaseModel):
    id: int
    repo_name: str
    local_path: Optional[str] = None
    created_at: str


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
