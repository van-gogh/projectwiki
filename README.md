# ProjectWiki

ProjectWiki is an open-source **AI-maintained Project Wiki** for messy software projects.

It turns local project documents and code into:

- source-backed blocks
- project facts
- AI/wiki-ready Markdown pages
- conflict reports
- handover packs
- evidence-backed Q&A

This repository is intentionally small. It is designed for Codex / Claude Code / OpenCode style coding agents to extend.

## Current first-board scope

Implemented as a runnable skeleton:

- SQLite metadata store
- local file ingestion
- local Git repo ingestion through the same file walker
- parsers for Markdown, text, CSV, Python/source code
- optional parsers for PDF, DOCX, XLSX if dependencies are installed
- deterministic fact extraction
- deterministic conflict detection
- Markdown Wiki generation
- handover pack generation
- naive evidence-backed Q&A
- FastAPI API surface
- static Web UI placeholder
- CLI commands
- Dockerfile and docker-compose
- Codex task guide in `docs/CODEX_TASKS.md`

Not yet implemented deeply:

- production-grade LLM calls
- vector search
- online spreadsheet connectors
- GitHub/GitLab/Gitea connectors
- permissions, SSO, audit logs, multi-tenancy
- advanced AST analysis beyond Python basics
- async worker queue

## Product startup target

First run:

```bash
npm install -g projectwiki
projectwiki
```

`projectwiki` should quietly start the local Web app and print a clickable local URL:

```text
ProjectWiki is running locally.

Open:
http://127.0.0.1:8765

Logs:
projectwiki log
```

All normal work should happen in the Web dashboard after startup. `projectwiki log` should show the current or most recent startup logs.

Open the printed local URL, click `Use demo project`, then inspect Conflicts, Wiki, Handover, and Ask with evidence.

## Current developer setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
projectwiki init-db
projectwiki create "Demo Project"
projectwiki ingest <PROJECT_ID> ./examples/demo-project
projectwiki build <PROJECT_ID>
projectwiki ask <PROJECT_ID> "这个项目当前有哪些冲突？"
projectwiki serve
```

Open <http://localhost:8080>.

## Docker developer setup

```bash
docker compose up --build
```

## Recommended Codex workflow

1. Read `AGENTS.md`.
2. Read `docs/CODEX_TASKS.md`.
3. Start with one task at a time.
4. After each task, run:

```bash
python -m compileall projectwiki
python -m pytest -q
```

## Architecture

```text
Sources
  -> Source Blocks
  -> Project Facts
  -> Wiki Pages / Conflicts / Handover / Ask
```

Markdown is an output format, not the internal source of truth. The internal truth is source-backed blocks and facts.
