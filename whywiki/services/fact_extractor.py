from __future__ import annotations

import re
import sqlite3

from ..db import connect, init_db
from ..utils import compact_text, from_json, new_id, now_iso, to_json

ENDPOINT_RE = re.compile(r"\b(GET|POST|PUT|PATCH|DELETE)\s+(/[A-Za-z0-9_/{}/.:-]+)", re.IGNORECASE)


def classify_fact(block_type: str, text: str) -> tuple[str, float]:
    t = text.lower()
    if "endpoint" in block_type or ENDPOINT_RE.search(text):
        return "api", 0.82
    if block_type.startswith("code_") or "function" in t or "class" in t or "import" in t:
        return "code", 0.78
    if any(k in text for k in ["需求", "用户故事", "Requirement", "requirement"]):
        return "requirement", 0.72
    if any(k in t for k in ["experiment", "f1", "accuracy", "dataset", "model", "模型", "实验"]):
        return "experiment", 0.7
    if any(k in t for k in ["deploy", "docker", "k8s", "kubernetes", "上线", "部署"]):
        return "deployment", 0.7
    if any(k in text for k in ["决定", "原因", "decision", "why", "废弃", "deprecated"]):
        return "decision", 0.68
    if block_type in {"table_row"}:
        return "record", 0.65
    return "document", 0.55


def rebuild_facts(project_id: str, conn: sqlite3.Connection | None = None) -> dict:
    close = conn is None
    conn = conn or connect()
    init_db(conn)
    conn.execute("DELETE FROM facts WHERE project_id = ?", (project_id,))

    rows = conn.execute(
        """
        SELECT b.*, s.path AS source_path, s.title AS source_title
        FROM blocks b
        JOIN sources s ON s.id = b.source_id
        WHERE b.project_id = ?
        ORDER BY s.path
        """,
        (project_id,),
    ).fetchall()

    inserted = 0
    for row in rows:
        fact_type, confidence = classify_fact(row["block_type"], row["text"])
        statement = make_statement(fact_type, row["block_type"], row["text"], row["source_title"])
        evidence = [
            {
                "source_id": row["source_id"],
                "block_id": row["id"],
                "path": row["source_path"],
                "location": from_json(row["location_json"], {}),
            }
        ]
        conn.execute(
            """
            INSERT INTO facts(id, project_id, fact_type, statement, evidence_json, status, confidence, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (new_id("fact"), project_id, fact_type, statement, to_json(evidence), "candidate", confidence, now_iso()),
        )
        inserted += 1

    conn.commit()
    if close:
        conn.close()
    return {"project_id": project_id, "facts_created": inserted}


def make_statement(fact_type: str, block_type: str, text: str, source_title: str) -> str:
    preview = compact_text(text, 500)
    if fact_type == "api":
        return f"材料 `{source_title}` 中记录了接口相关信息：{preview}"
    if fact_type == "code":
        return f"代码材料 `{source_title}` 中存在代码结构信息：{preview}"
    if fact_type == "requirement":
        return f"材料 `{source_title}` 中记录了需求相关信息：{preview}"
    if fact_type == "experiment":
        return f"材料 `{source_title}` 中记录了实验/模型相关信息：{preview}"
    if fact_type == "deployment":
        return f"材料 `{source_title}` 中记录了部署相关信息：{preview}"
    if fact_type == "decision":
        return f"材料 `{source_title}` 中记录了决策或变更原因：{preview}"
    return f"材料 `{source_title}` 中记录了项目事实：{preview}"
