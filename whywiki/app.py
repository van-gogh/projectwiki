from __future__ import annotations

from importlib import resources
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .collaboration.accounts import AccountStore
from .collaboration.artifacts import (
    WorkspaceArtifactPaths,
    load_workspace_config,
    save_workspace_config,
)
from .collaboration.models import RepoRef, WorkspaceConfig
from .config import get_data_dir
from .db import connect, init_db, rows_to_dicts
from .services.ask import ask_project
from .services.ingest import ingest_path
from .services.wiki_engine import build_project
from .services.workspace import create_project, get_project, list_projects

app = FastAPI(title="WhyWiki", version="0.1.0")
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


class ConflictStatusRequest(BaseModel):
    status: str


class ConnectWorkspaceRequest(BaseModel):
    provider: str
    repo: str
    base_url: str | None = None


def account_store() -> AccountStore:
    return AccountStore(get_data_dir() / "auth" / "accounts.json")


def workspace_paths() -> WorkspaceArtifactPaths:
    return WorkspaceArtifactPaths(get_data_dir() / "workspace")


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return (static_dir / "index.html").read_text(encoding="utf-8")


def demo_project_root() -> Any:
    return resources.files("whywiki").joinpath("demo_project")


@app.post("/api/demo")
def api_demo() -> dict:
    root = demo_project_root()
    with resources.as_file(root) as root_path:
        if not root_path.exists() or not root_path.is_dir():
            raise HTTPException(status_code=500, detail=f"Demo project assets not found: {root}")
        project = create_project("Demo Project", "Messy sample project for WhyWiki")
        ingest = ingest_path(project["id"], root_path)
    build = build_project(project["id"])
    return {"project": project, "ingest": ingest, "build": build}


@app.post("/api/projects")
def api_create_project(req: CreateProjectRequest) -> dict:
    return create_project(req.name, req.description)


@app.get("/api/projects")
def api_list_projects() -> list[dict]:
    return list_projects()


@app.get("/api/auth/accounts")
def api_auth_accounts() -> dict:
    return {
        "connected_accounts": [
            identity.to_dict()
            for identity in account_store().list_identities()
        ]
    }


@app.post("/api/workspace/connect")
def api_connect_workspace(req: ConnectWorkspaceRequest) -> dict:
    try:
        config = WorkspaceConfig(
            workspace=RepoRef(
                provider=req.provider,
                repo=req.repo,
                base_url=req.base_url,
            )
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    save_workspace_config(workspace_paths(), config)
    return {"workspace": config.workspace.to_dict()}


@app.get("/api/workspace/status")
def api_workspace_status() -> dict:
    paths = workspace_paths()
    if not paths.workspace_config_path.exists():
        return {"configured": False, "workspace": None, "projects": {}}
    return {"configured": True, **load_workspace_config(paths).to_dict()}


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


@app.get("/api/projects/{project_id}/sources")
def api_list_sources(project_id: str) -> list[dict]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM sources WHERE project_id = ? ORDER BY path",
            (project_id,),
        ).fetchall()
        return rows_to_dicts(rows)


@app.get("/api/projects/{project_id}/sources/{source_id}/blocks")
def api_list_source_blocks(project_id: str, source_id: str) -> list[dict]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT * FROM blocks
            WHERE project_id = ? AND source_id = ?
            ORDER BY id
            """,
            (project_id, source_id),
        ).fetchall()
        return rows_to_dicts(rows)


@app.get("/api/projects/{project_id}/facts")
def api_list_facts(project_id: str) -> list[dict]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM facts WHERE project_id = ? ORDER BY fact_type, confidence DESC",
            (project_id,),
        ).fetchall()
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


@app.patch("/api/projects/{project_id}/conflicts/{conflict_id}")
def api_update_conflict(project_id: str, conflict_id: str, req: ConflictStatusRequest) -> dict:
    if req.status not in {"open", "resolved", "ignored"}:
        raise HTTPException(status_code=400, detail="Invalid conflict status")
    with connect() as conn:
        row = conn.execute(
            "SELECT id FROM conflicts WHERE project_id = ? AND id = ?",
            (project_id, conflict_id),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Conflict not found")
        conn.execute(
            "UPDATE conflicts SET status = ? WHERE project_id = ? AND id = ?",
            (req.status, project_id, conflict_id),
        )
        conn.commit()
        return {"id": conflict_id, "status": req.status}


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
