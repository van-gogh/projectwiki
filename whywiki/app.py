from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .db import connect, init_db, rows_to_dicts
from .services.ask import ask_project
from .services.evidence import conflict_evidence, fact_evidence
from .services.ingest import ingest_path
from .services.jobs import create_job, get_job, start_background_job
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


class FactStatusRequest(BaseModel):
    status: str


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


@app.post("/api/projects/{project_id}/ingest-jobs")
def api_start_ingest_job(project_id: str, req: IngestRequest) -> dict:
    try:
        get_project(project_id)
        job = create_job(project_id, "ingest", "Queued project scan.")
        start_background_job(
            job["id"],
            lambda: ingest_path(project_id, req.path, req.source_type),
            "Scanning project source.",
            "Project source scanned.",
        )
        return get_job(job["id"])
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/projects/{project_id}/build")
def api_build(project_id: str) -> dict:
    try:
        get_project(project_id)
        return build_project(project_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/projects/{project_id}/build-jobs")
def api_start_build_job(project_id: str) -> dict:
    try:
        get_project(project_id)
        job = create_job(project_id, "build", "Queued Wiki generation.")
        start_background_job(
            job["id"],
            lambda: build_project(project_id),
            "Generating evidence-backed Wiki.",
            "Evidence-backed Wiki generated.",
        )
        return get_job(job["id"])
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/jobs/{job_id}")
def api_get_job(job_id: str) -> dict:
    try:
        return get_job(job_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


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


@app.patch("/api/projects/{project_id}/facts/{fact_id}")
def api_update_fact(project_id: str, fact_id: str, req: FactStatusRequest) -> dict:
    if req.status not in {"candidate", "confirmed", "needs_review"}:
        raise HTTPException(status_code=400, detail="Invalid fact status")
    validity_status = "current" if req.status == "confirmed" else "unknown"
    with connect() as conn:
        row = conn.execute(
            "SELECT id FROM facts WHERE project_id = ? AND id = ?",
            (project_id, fact_id),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Fact not found")
        conn.execute(
            "UPDATE facts SET status = ?, validity_status = ? WHERE project_id = ? AND id = ?",
            (req.status, validity_status, project_id, fact_id),
        )
        conn.commit()
        updated = conn.execute(
            "SELECT * FROM facts WHERE project_id = ? AND id = ?",
            (project_id, fact_id),
        ).fetchone()
        return dict(updated)


@app.get("/api/projects/{project_id}/facts/{fact_id}/evidence")
def api_fact_evidence(project_id: str, fact_id: str) -> list[dict]:
    try:
        return fact_evidence(project_id, fact_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


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


@app.get("/api/projects/{project_id}/conflicts/{conflict_id}/evidence")
def api_conflict_evidence(project_id: str, conflict_id: str) -> list[dict]:
    try:
        return conflict_evidence(project_id, conflict_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


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
