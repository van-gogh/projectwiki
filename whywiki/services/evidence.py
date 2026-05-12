from __future__ import annotations

import sqlite3
from typing import Any

from ..db import connect, init_db
from ..utils import from_json


def resolve_evidence_items(project_id: str, evidence_items: list[dict[str, Any]], conn: sqlite3.Connection | None = None) -> list[dict]:
    close = conn is None
    conn = conn or connect()
    init_db(conn)
    resolved = []

    for item in evidence_items:
        if not isinstance(item, dict):
            continue
        source_id = item.get("source_id")
        block_id = item.get("block_id")
        source = None
        block = None
        if source_id:
            source = conn.execute(
                "SELECT * FROM sources WHERE project_id = ? AND id = ?",
                (project_id, source_id),
            ).fetchone()
        if block_id:
            block = conn.execute(
                "SELECT * FROM blocks WHERE project_id = ? AND id = ?",
                (project_id, block_id),
            ).fetchone()
            if source is None and block is not None:
                source = conn.execute(
                    "SELECT * FROM sources WHERE project_id = ? AND id = ?",
                    (project_id, block["source_id"]),
                ).fetchone()

        resolved.append(
            {
                "source_id": source["id"] if source else source_id,
                "block_id": block["id"] if block else block_id,
                "path": source["path"] if source else item.get("path", "unknown"),
                "source_type": source["source_type"] if source else item.get("source_type", "unknown"),
                "source_title": source["title"] if source else item.get("title", ""),
                "location": from_json(block["location_json"], {}) if block else item.get("location", {}),
                "block_type": block["block_type"] if block else "",
                "block_text": block["text"] if block else "",
                "metadata": from_json(block["metadata_json"], {}) if block else {},
            }
        )

    if close:
        conn.close()
    return resolved


def fact_evidence(project_id: str, fact_id: str, conn: sqlite3.Connection | None = None) -> list[dict]:
    close = conn is None
    conn = conn or connect()
    init_db(conn)
    row = conn.execute(
        "SELECT evidence_json FROM facts WHERE project_id = ? AND id = ?",
        (project_id, fact_id),
    ).fetchone()
    if not row:
        if close:
            conn.close()
        raise ValueError("Fact not found")
    evidence = resolve_evidence_items(project_id, from_json(row["evidence_json"], []), conn)
    if close:
        conn.close()
    return evidence


def conflict_evidence(project_id: str, conflict_id: str, conn: sqlite3.Connection | None = None) -> list[dict]:
    close = conn is None
    conn = conn or connect()
    init_db(conn)
    row = conn.execute(
        "SELECT evidence_json FROM conflicts WHERE project_id = ? AND id = ?",
        (project_id, conflict_id),
    ).fetchone()
    if not row:
        if close:
            conn.close()
        raise ValueError("Conflict not found")
    evidence = resolve_evidence_items(project_id, from_json(row["evidence_json"], []), conn)
    if close:
        conn.close()
    return evidence
