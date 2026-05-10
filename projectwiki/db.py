from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable

from .config import get_db_path


def connect(db_path: Path | None = None) -> sqlite3.Connection:
    path = db_path or get_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(conn: sqlite3.Connection | None = None) -> None:
    close = conn is None
    conn = conn or connect()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS projects (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS sources (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            source_type TEXT NOT NULL,
            path TEXT NOT NULL,
            title TEXT DEFAULT '',
            content_hash TEXT NOT NULL,
            metadata_json TEXT DEFAULT '{}',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(project_id, path)
        );

        CREATE TABLE IF NOT EXISTS blocks (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            source_id TEXT NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
            block_type TEXT NOT NULL,
            text TEXT NOT NULL,
            location_json TEXT DEFAULT '{}',
            metadata_json TEXT DEFAULT '{}',
            content_hash TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS facts (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            fact_type TEXT NOT NULL,
            statement TEXT NOT NULL,
            evidence_json TEXT DEFAULT '[]',
            status TEXT DEFAULT 'candidate',
            confidence REAL DEFAULT 0.5,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS conflicts (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            conflict_type TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            evidence_json TEXT DEFAULT '[]',
            severity TEXT DEFAULT 'medium',
            status TEXT DEFAULT 'open',
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS wiki_pages (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            slug TEXT NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(project_id, slug)
        );

        CREATE INDEX IF NOT EXISTS idx_sources_project ON sources(project_id);
        CREATE INDEX IF NOT EXISTS idx_blocks_project ON blocks(project_id);
        CREATE INDEX IF NOT EXISTS idx_blocks_source ON blocks(source_id);
        CREATE INDEX IF NOT EXISTS idx_facts_project ON facts(project_id);
        CREATE INDEX IF NOT EXISTS idx_conflicts_project ON conflicts(project_id);
        CREATE INDEX IF NOT EXISTS idx_wiki_project ON wiki_pages(project_id);
        """
    )
    conn.commit()
    if close:
        conn.close()


def rows_to_dicts(rows: Iterable[sqlite3.Row]) -> list[dict]:
    return [dict(row) for row in rows]
