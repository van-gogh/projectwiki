from __future__ import annotations

import difflib
import re
import sqlite3
from collections import defaultdict

from ..db import connect, init_db
from ..utils import from_json, new_id, now_iso, to_json

ENDPOINT_RE = re.compile(r"\b(GET|POST|PUT|PATCH|DELETE)\s+(/[A-Za-z0-9_/{}/.:-]+)", re.IGNORECASE)
FILE_MENTION_RE = re.compile(r"\b[\w./-]+\.(?:py|sh|yaml|yml|json|toml|md|sql)\b")
MODEL_WORDS = ["LSTM", "Transformer", "BERT", "CNN", "RNN", "XGBoost", "LightGBM"]
LATEST_HINTS = ["latest", "最新版", "最终版", "final", "current", "当前版本"]


def detect_conflicts(project_id: str, conn: sqlite3.Connection | None = None) -> dict:
    close = conn is None
    conn = conn or connect()
    init_db(conn)
    conn.execute("DELETE FROM conflicts WHERE project_id = ?", (project_id,))

    inserted = 0
    inserted += detect_multiple_latest_docs(project_id, conn)
    inserted += detect_endpoint_conflicts(project_id, conn)
    inserted += detect_model_term_conflicts(project_id, conn)
    inserted += detect_missing_file_mentions(project_id, conn)

    conn.commit()
    if close:
        conn.close()
    return {"project_id": project_id, "conflicts_created": inserted}


def insert_conflict(conn: sqlite3.Connection, project_id: str, conflict_type: str, title: str, description: str, evidence: list, severity: str = "medium") -> None:
    conn.execute(
        """
        INSERT INTO conflicts(id, project_id, conflict_type, title, description, evidence_json, severity, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (new_id("conf"), project_id, conflict_type, title, description, to_json(evidence), severity, "open", now_iso()),
    )


def detect_multiple_latest_docs(project_id: str, conn: sqlite3.Connection) -> int:
    rows = conn.execute("SELECT id, path, title FROM sources WHERE project_id = ?", (project_id,)).fetchall()
    latest_like = [r for r in rows if any(h.lower() in (r["path"] + r["title"]).lower() for h in LATEST_HINTS)]
    if len(latest_like) <= 1:
        return 0
    evidence = [{"source_id": r["id"], "path": r["path"]} for r in latest_like]
    insert_conflict(
        conn,
        project_id,
        "multiple_latest_documents",
        "多个材料都声称自己是最新版或最终版",
        "系统发现多个文件名或标题包含 latest/final/最新版/最终版 等线索，需要人工确认当前有效版本。",
        evidence,
        "high",
    )
    return 1


def detect_endpoint_conflicts(project_id: str, conn: sqlite3.Connection) -> int:
    rows = conn.execute(
        """
        SELECT b.id AS block_id, b.text, b.location_json, s.id AS source_id, s.path
        FROM blocks b JOIN sources s ON s.id = b.source_id
        WHERE b.project_id = ?
        """,
        (project_id,),
    ).fetchall()
    endpoints = []
    for r in rows:
        for m in ENDPOINT_RE.finditer(r["text"]):
            endpoints.append({
                "method": m.group(1).upper(),
                "path_value": m.group(2),
                "source_id": r["source_id"],
                "block_id": r["block_id"],
                "path": r["path"],
                "location": from_json(r["location_json"], {}),
            })
    by_method: dict[str, list[dict]] = defaultdict(list)
    for ep in endpoints:
        by_method[ep["method"]].append(ep)

    count = 0
    seen_pairs = set()
    for method, eps in by_method.items():
        for i in range(len(eps)):
            for j in range(i + 1, len(eps)):
                a, b = eps[i], eps[j]
                if a["path_value"] == b["path_value"]:
                    continue
                ratio = difflib.SequenceMatcher(None, a["path_value"], b["path_value"]).ratio()
                pair_key = tuple(sorted([a["path_value"], b["path_value"]]))
                if ratio >= 0.78 and pair_key not in seen_pairs:
                    seen_pairs.add(pair_key)
                    insert_conflict(
                        conn,
                        project_id,
                        "endpoint_mismatch",
                        f"疑似接口路径不一致：{method} {a['path_value']} vs {b['path_value']}",
                        "两个材料中出现了高度相似但不完全一致的接口路径，可能是文档过期或代码变更未同步。",
                        [a, b],
                        "medium",
                    )
                    count += 1
    return count


def detect_model_term_conflicts(project_id: str, conn: sqlite3.Connection) -> int:
    rows = conn.execute(
        """
        SELECT b.id AS block_id, b.text, s.id AS source_id, s.path
        FROM blocks b JOIN sources s ON s.id = b.source_id
        WHERE b.project_id = ?
        """,
        (project_id,),
    ).fetchall()
    hits: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        lower = r["text"].lower()
        if not any(k in lower for k in ["model", "模型", "architecture", "架构", "experiment", "实验"]):
            continue
        for word in MODEL_WORDS:
            if word.lower() in lower:
                hits[word].append({"source_id": r["source_id"], "block_id": r["block_id"], "path": r["path"]})
    active_words = [word for word, ev in hits.items() if ev]
    if len(active_words) <= 1:
        return 0
    evidence = []
    for word in active_words:
        evidence.extend(hits[word][:2])
    insert_conflict(
        conn,
        project_id,
        "model_architecture_mismatch",
        f"疑似模型架构记录不一致：{', '.join(active_words)}",
        "多个材料在模型/实验语境中提到了不同架构词，需要确认当前有效模型版本。",
        evidence,
        "medium",
    )
    return 1


def detect_missing_file_mentions(project_id: str, conn: sqlite3.Connection) -> int:
    sources = conn.execute("SELECT path FROM sources WHERE project_id = ?", (project_id,)).fetchall()
    known_paths = {r["path"] for r in sources}
    known_names = {p.split("/")[-1].split("\\")[-1] for p in known_paths}
    rows = conn.execute(
        """
        SELECT b.id AS block_id, b.text, s.id AS source_id, s.path
        FROM blocks b JOIN sources s ON s.id = b.source_id
        WHERE b.project_id = ?
        """,
        (project_id,),
    ).fetchall()
    missing = []
    for r in rows:
        for m in FILE_MENTION_RE.finditer(r["text"]):
            mention = m.group(0).strip("`.,;:()[]{}")
            if mention.startswith(("http", "./.venv")):
                continue
            basename = mention.split("/")[-1]
            if basename not in known_names and mention not in known_paths:
                missing.append({"mention": mention, "source_id": r["source_id"], "block_id": r["block_id"], "path": r["path"]})
    if not missing:
        return 0
    insert_conflict(
        conn,
        project_id,
        "missing_mentioned_file",
        "材料中提到的部分文件未在已摄入来源中找到",
        "文档提到了一些脚本或配置文件，但系统未在当前项目来源中找到对应文件。可能是文件缺失、路径变化或未摄入完整材料。",
        missing[:20],
        "low",
    )
    return 1
