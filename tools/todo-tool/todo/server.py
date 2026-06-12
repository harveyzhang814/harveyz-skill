import sys
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .db import TodoDB
from .models import Project, ProjectCreate, ProjectUpdate, Task, TaskCreate, TaskUpdate


def create_app(db: TodoDB = None) -> FastAPI:
    if db is None:
        db = TodoDB()

    app = FastAPI(title="Todo Tool")

    # ── Project endpoints ─────────────────────────────────────────────────────

    @app.get("/api/projects", response_model=list[Project])
    def list_projects():
        return db.list_projects()

    @app.post("/api/projects", response_model=Project, status_code=201)
    def create_project(data: ProjectCreate):
        return db.create_project(data)

    @app.patch("/api/projects/{project_id}", response_model=Project)
    def update_project(project_id: int, data: ProjectUpdate):
        project = db.update_project(project_id, data)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        return project

    @app.delete("/api/projects/{project_id}", status_code=204)
    def delete_project(project_id: int):
        try:
            if not db.delete_project(project_id):
                raise HTTPException(status_code=404, detail="Project not found")
        except ValueError as e:
            raise HTTPException(status_code=409, detail=str(e))

    # ── Task endpoints ────────────────────────────────────────────────────────

    @app.get("/api/tasks", response_model=list[Task])
    def list_tasks(
        project: Optional[str] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
    ):
        for proj in db.list_projects():
            if proj.local_path:
                todo_md = Path(proj.local_path) / "TODO.md"
                if todo_md.exists():
                    try:
                        db.sync_from_file(todo_md, proj.id)
                    except Exception as e:
                        print(f"Warning: sync failed for {proj.repo_name}: {e}", file=sys.stderr)
        return db.list_tasks(project=project, status=status, priority=priority)

    @app.post("/api/tasks", response_model=Task, status_code=201)
    def create_task(data: TaskCreate):
        try:
            return db.create(data)
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))

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

    # ── Frontend ──────────────────────────────────────────────────────────────

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
