from __future__ import annotations

import re
import sqlite3

from ..db import connect, init_db
from ..utils import from_json


def tokenize(text: str) -> set[str]:
    # Works for English and coarse Chinese matching through character ngrams.
    words = set(re.findall(r"[A-Za-z0-9_/-]{2,}", text.lower()))
    chinese_chars = re.findall(r"[\u4e00-\u9fff]", text)
    words.update(chinese_chars)
    return words


def ask_project(project_id: str, question: str, conn: sqlite3.Connection | None = None, limit: int = 6) -> dict:
    close = conn is None
    conn = conn or connect()
    init_db(conn)
    q_tokens = tokenize(question)

    candidates = []
    for row in conn.execute(
        """
        SELECT f.*, NULL AS block_text
        FROM facts f WHERE f.project_id = ?
        """,
        (project_id,),
    ).fetchall():
        tokens = tokenize(row["statement"])
        score = len(q_tokens & tokens) + float(row["confidence"])
        if score > 0:
            candidates.append((score, "fact", row))

    for row in conn.execute(
        """
        SELECT b.*, s.path AS source_path
        FROM blocks b JOIN sources s ON s.id = b.source_id
        WHERE b.project_id = ?
        """,
        (project_id,),
    ).fetchall():
        tokens = tokenize(row["text"])
        score = len(q_tokens & tokens)
        if score > 0:
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
