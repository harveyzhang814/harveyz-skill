from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .db import TodoDB
from .models import Task, TaskCreate, TaskUpdate


def create_app(db: TodoDB = None) -> FastAPI:
    if db is None:
        db = TodoDB()

    app = FastAPI(title="Todo Tool")

    @app.get("/api/tasks", response_model=list[Task])
    def list_tasks(
        project: Optional[str] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
    ):
        return db.list_tasks(project=project, status=status, priority=priority)

    @app.post("/api/tasks", response_model=Task, status_code=201)
    def create_task(data: TaskCreate):
        return db.create(data)

    @app.patch("/api/tasks/{task_id}", response_model=Task)
    def update_task(task_id: int, data: TaskUpdate):
        task = db.update(task_id, data)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        return task

    @app.delete("/api/tasks/{task_id}", status_code=204)
    def delete_task(task_id: int):
        if not db.delete(task_id):
            raise HTTPException(status_code=404, detail="Task not found")

    @app.get("/api/projects", response_model=list[str])
    def list_projects():
        return db.projects()

    # Serve React frontend (populated after Task 6)
    frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
    if frontend_dist.exists():
        app.mount(
            "/assets",
            StaticFiles(directory=frontend_dist / "assets"),
            name="assets",
        )

        @app.get("/{full_path:path}")
        def serve_frontend(full_path: str):
            return FileResponse(frontend_dist / "index.html")

    return app
