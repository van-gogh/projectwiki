from __future__ import annotations

import re
import sqlite3

from ..db import connect, init_db
from ..utils import from_json

MIN_TOKEN_OVERLAP = 2
HTTP_METHODS = {"get", "post", "put", "patch", "delete"}
PRICING_INTENT_TERMS = (
    "预算",
    "收费",
    "费用",
    "价格",
    "budget",
    "cost",
    "pricing",
    "price",
)
CONFLICT_INTENT_TERMS = (
    "冲突",
    "待审查",
    "review",
    "conflict",
    "conflicts",
)
SEVERITY_SCORES = {
    "high": 3.0,
    "medium": 2.0,
    "low": 1.0,
}


def tokenize(text: str) -> set[str]:
    # Works for English and coarse Chinese matching through character ngrams.
    words = set(re.findall(r"[A-Za-z0-9_/-]{2,}", text.lower()))
    chinese_chars = re.findall(r"[\u4e00-\u9fff]", text)
    words.update(chinese_chars)
    return words


def has_pricing_intent(text: str) -> bool:
    lower = text.lower()
    return any(term in lower for term in PRICING_INTENT_TERMS)


def has_conflict_intent(text: str) -> bool:
    lower = text.lower()
    return any(term in lower for term in CONFLICT_INTENT_TERMS)


def conflict_evidence_paths(evidence_json: str) -> list[str]:
    paths = []
    for item in from_json(evidence_json, []):
        path = item.get("path") if isinstance(item, dict) else None
        if path and path not in paths:
            paths.append(path)
    return paths


def answer_conflict_question(project_id: str, question: str, conn: sqlite3.Connection) -> dict | None:
    if not has_conflict_intent(question):
        return None

    rows = conn.execute(
        """
        SELECT * FROM conflicts
        WHERE project_id = ? AND status = 'open'
        ORDER BY
          CASE severity WHEN 'high' THEN 0 WHEN 'medium' THEN 1 ELSE 2 END,
          created_at DESC
        """,
        (project_id,),
    ).fetchall()

    if not rows:
        return {
            "question": question,
            "answer": "当前没有检测到 open 的待审查冲突。",
            "evidence": [],
        }

    bullets = []
    evidence = []
    for row in rows:
        paths = conflict_evidence_paths(row["evidence_json"])
        evidence_text = "、".join(f"`{path}`" for path in paths) if paths else "`unknown`"
        bullets.append(
            f"- **{row['title']}**（{row['severity']}）\n"
            f"  - {row['description']}\n"
            f"  - 证据：{evidence_text}"
        )
        evidence.append(
            {
                "kind": "conflict",
                "id": row["id"],
                "path": paths[0] if paths else "unknown",
                "paths": paths,
                "score": SEVERITY_SCORES.get(row["severity"], 0.0),
            }
        )

    answer = "我只能基于当前已摄入材料回答。当前检测到以下待审查冲突：\n\n" + "\n".join(bullets)
    return {"question": question, "answer": answer, "evidence": evidence}


def is_api_evidence(row, tokens: set[str]) -> bool:
    block_type = row["block_type"] if "block_type" in row.keys() else ""
    fact_type = row["fact_type"] if "fact_type" in row.keys() else ""
    return fact_type == "api" or "endpoint" in block_type or bool(HTTP_METHODS & tokens)


def should_include_candidate(question_tokens: set[str], candidate_tokens: set[str], score: float, row) -> bool:
    overlap = len(question_tokens & candidate_tokens)
    if question_tokens <= HTTP_METHODS:
        return bool(question_tokens & candidate_tokens) and is_api_evidence(row, candidate_tokens)
    if overlap >= MIN_TOKEN_OVERLAP:
        return True
    if len(question_tokens) == 1 and overlap == 1:
        return True
    return score >= MIN_TOKEN_OVERLAP


def ask_project(project_id: str, question: str, conn: sqlite3.Connection | None = None, limit: int = 6) -> dict:
    close = conn is None
    conn = conn or connect()
    init_db(conn)
    q_tokens = tokenize(question)
    requires_pricing_evidence = has_pricing_intent(question)
    conflict_answer = answer_conflict_question(project_id, question, conn)
    if conflict_answer is not None:
        if close:
            conn.close()
        return conflict_answer

    candidates = []
    for row in conn.execute(
        """
        SELECT f.*, NULL AS block_text
        FROM facts f WHERE f.project_id = ?
        """,
        (project_id,),
    ).fetchall():
        if requires_pricing_evidence and not has_pricing_intent(row["statement"]):
            continue
        tokens = tokenize(row["statement"])
        score = len(q_tokens & tokens) + float(row["confidence"])
        if should_include_candidate(q_tokens, tokens, score, row):
            candidates.append((score, "fact", row))

    for row in conn.execute(
        """
        SELECT b.*, s.path AS source_path
        FROM blocks b JOIN sources s ON s.id = b.source_id
        WHERE b.project_id = ?
        """,
        (project_id,),
    ).fetchall():
        if requires_pricing_evidence and not has_pricing_intent(row["text"]):
            continue
        tokens = tokenize(row["text"])
        score = len(q_tokens & tokens)
        if should_include_candidate(q_tokens, tokens, score, row):
            candidates.append((score, "block", row))

    candidates.sort(key=lambda x: x[0], reverse=True)
    top = candidates[:limit]

    evidence = []
    bullets = []
    for score, kind, row in top:
        if kind == "fact":
            ev = from_json(row["evidence_json"], [])
            path = ev[0].get("path", "unknown") if ev else "unknown"
            bullets.append(f"- {row['statement']}\n  - 证据：`{path}`")
            evidence.append({"kind": "fact", "id": row["id"], "path": path, "score": score})
        else:
            text = row["text"].strip().replace("\n", " ")
            if len(text) > 240:
                text = text[:239] + "…"
            bullets.append(f"- {text}\n  - 证据：`{row['source_path']}`")
            evidence.append({"kind": "block", "id": row["id"], "path": row["source_path"], "score": score})

    if bullets:
        answer = "我只能基于当前已摄入材料回答。相关证据如下：\n\n" + "\n".join(bullets)
    else:
        answer = "当前已摄入材料中没有找到足够证据回答这个问题。建议补充材料或换一个更具体的问题。"

    if close:
        conn.close()
    return {"question": question, "answer": answer, "evidence": evidence}
