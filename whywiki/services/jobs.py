from __future__ import annotations

from collections.abc import Callable
import sqlite3
import threading
from typing import Any

from ..db import connect, init_db
from ..utils import from_json, new_id, now_iso, to_json


TERMINAL_STATUSES = {"succeeded", "failed"}


def serialize_job(row: sqlite3.Row) -> dict:
    payload = dict(row)
    payload["result"] = from_json(payload.pop("result_json", "{}"), {})
    return payload


def create_job(project_id: str, operation_type: str, message: str = "") -> dict:
    with connect() as conn:
        init_db(conn)
        now = now_iso()
        job_id = new_id("job")
        conn.execute(
            """
            INSERT INTO operation_jobs(id, project_id, operation_type, status, progress, message, result_json, error, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (job_id, project_id, operation_type, "queued", 0, message, "{}", "", now, now),
        )
        conn.commit()
        return get_job(job_id, conn)


def get_job(job_id: str, conn: sqlite3.Connection | None = None) -> dict:
    close = conn is None
    conn = conn or connect()
    init_db(conn)
    row = conn.execute("SELECT * FROM operation_jobs WHERE id = ?", (job_id,)).fetchone()
    if close:
        conn.close()
    if not row:
        raise ValueError(f"Job not found: {job_id}")
    return serialize_job(row)


def update_job(
    job_id: str,
    *,
    status: str | None = None,
    progress: int | None = None,
    message: str | None = None,
    result: dict[str, Any] | None = None,
    error: str | None = None,
) -> dict:
    with connect() as conn:
        init_db(conn)
        current = conn.execute("SELECT * FROM operation_jobs WHERE id = ?", (job_id,)).fetchone()
        if not current:
            raise ValueError(f"Job not found: {job_id}")
        conn.execute(
            """
            UPDATE operation_jobs
            SET status = ?, progress = ?, message = ?, result_json = ?, error = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                status if status is not None else current["status"],
                progress if progress is not None else current["progress"],
                message if message is not None else current["message"],
                to_json(result) if result is not None else current["result_json"],
                error if error is not None else current["error"],
                now_iso(),
                job_id,
            ),
        )
        conn.commit()
        return get_job(job_id, conn)


def run_job(job_id: str, operation: Callable[[], dict], running_message: str, success_message: str) -> None:
    try:
        update_job(job_id, status="running", progress=15, message=running_message)
        result = operation()
        update_job(job_id, status="succeeded", progress=100, message=success_message, result=result, error="")
    except Exception as exc:
        update_job(job_id, status="failed", progress=100, message=str(exc), error=str(exc))


def start_background_job(job_id: str, operation: Callable[[], dict], running_message: str, success_message: str) -> None:
    thread = threading.Thread(
        target=run_job,
        args=(job_id, operation, running_message, success_message),
        daemon=True,
        name=f"whywiki-job-{job_id}",
    )
    thread.start()
