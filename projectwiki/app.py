from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .db import connect, init_db, rows_to_dicts
from .services.ask import ask_project
from .services.ingest import ingest_path
from .services.wiki_engine import build_project
from .services.workspace import create_project, get_project, list_projects

app = FastAPI(title="ProjectWiki", version="0.1.0")
static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")


class CreateProjectRequest(BaseModel):
    name: str
    description: str = ""


class IngestRequest(BaseModel):
    path: str
    source_type: str = "local"


class AskRequest(BaseModel):
    question: str


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return (static_dir / "index.html").read_text(encoding="utf-8")


@app.post("/api/projects")
def api_create_project(req: CreateProjectRequest) -> dict:
    return create_project(req.name, req.description)


@app.get("/api/projects")
def api_list_projects() -> list[dict]:
    return list_projects()


@app.get("/api/projects/{project_id}")
def api_get_project(project_id: str) -> dict:
    try:
        return get_project(project_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/projects/{project_id}/ingest")
def api_ingest(project_id: str, req: IngestRequest) -> dict:
    try:
        get_project(project_id)
        return ingest_path(project_id, req.path, req.source_type)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/projects/{project_id}/build")
def api_build(project_id: str) -> dict:
    try:
        get_project(project_id)
        return build_project(project_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/projects/{project_id}/wiki")
def api_list_wiki(project_id: str) -> list[dict]:
    with connect() as conn:
        rows = conn.execute("SELECT slug, title, updated_at FROM wiki_pages WHERE project_id = ? ORDER BY slug", (project_id,)).fetchall()
        return rows_to_dicts(rows)


@app.get("/api/projects/{project_id}/wiki/{slug}", response_class=PlainTextResponse)
def api_get_wiki_page(project_id: str, slug: str) -> str:
    with connect() as conn:
        row = conn.execute("SELECT content FROM wiki_pages WHERE project_id = ? AND slug = ?", (project_id, slug)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Wiki page not found")
        return row["content"]


@app.get("/api/projects/{project_id}/conflicts")
def api_conflicts(project_id: str) -> list[dict]:
    with connect() as conn:
        rows = conn.execute("SELECT * FROM conflicts WHERE project_id = ? ORDER BY created_at DESC", (project_id,)).fetchall()
        return rows_to_dicts(rows)


@app.get("/api/projects/{project_id}/handover", response_class=PlainTextResponse)
def api_handover(project_id: str) -> str:
    with connect() as conn:
        row = conn.execute("SELECT content FROM wiki_pages WHERE project_id = ? AND slug = 'handover'", (project_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Handover page not found. Run build first.")
        return row["content"]


@app.post("/api/projects/{project_id}/ask")
def api_ask(project_id: str, req: AskRequest) -> dict:
    return ask_project(project_id, req.question)
