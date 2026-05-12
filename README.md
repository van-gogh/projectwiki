# WhyWiki

**A team wiki that remembers why.** ✨

Git remembers what changed. WhyWiki remembers why it changed.

WhyWiki turns scattered project materials into a living, evidence-backed wiki for messy software projects: requirements, code, decisions, conflicts, experiments, deployment notes, and handover context all in one local workspace.

It is built for small teams, labs, open-source maintainers, and solo developers who keep asking:

- "Which requirement is actually current?"
- "Why did we build it this way?"
- "Where did this decision come from?"
- "What changed, and what is now out of sync?"
- "How do I hand this project to the next person without losing the plot?"

## What WhyWiki Does

WhyWiki reads local files, docs, code, and Git repos, then builds a project memory you can inspect:

- 🔎 **Source-backed blocks** from Markdown, text, CSV, code, PDF, DOCX, and XLSX
- 🧠 **Project facts** extracted from the material, each with evidence
- ⚠️ **Conflict reports** for stale docs, mismatched APIs, missing files, and model/deployment drift
- 📚 **Wiki pages** generated from evidence, not vibes
- 📦 **Handover packs** for onboarding, audits, and project transfer
- 💬 **Ask with evidence** so answers point back to real files

WhyWiki is not trying to replace Git, Notion, Confluence, Feishu, GitHub, or your issue tracker. It sits beside them and remembers the project knowledge that usually leaks out of the system.

```text
local files / git repo / docs / code
  -> parsers
  -> source blocks
  -> project facts
  -> conflicts
  -> wiki pages / handover / ask
```

Markdown is an output format, not the internal source of truth. The internal truth is source-backed blocks and facts.

## Try The Preview

Install the preview package and start the local workspace:

```bash
npm install -g whywiki
whywiki
```

The command starts the local Web app and prints a local URL:

```text
WhyWiki is running locally.

Open:
http://127.0.0.1:8765

Logs:
whywiki log
```

Open the URL, click `Use demo project`, then inspect project status, conflicts, wiki pages, handover, sources, and Ask with evidence.

For local repository development, use the restart script:

```bash
./start.sh
```

The script creates or reuses `.venv`, installs WhyWiki locally, stops the old service on `127.0.0.1:8765`, initializes the SQLite database, and starts a fresh Web app on <http://127.0.0.1:8765>.

## Current First Board

The first board is already a runnable local skeleton:

- SQLite metadata store
- local file ingestion
- local Git repo ingestion through the same file walker
- parsers for Markdown, text, CSV, Python/source code
- optional parsers for PDF, DOCX, and XLSX if dependencies are installed
- deterministic fact extraction
- deterministic conflict detection
- Markdown wiki generation
- handover pack generation
- naive evidence-backed Q&A
- FastAPI API surface
- local Web dashboard
- CLI commands
- Dockerfile and docker-compose
- Codex task guide in `docs/CODEX_TASKS.md`

Still intentionally shallow:

- production-grade LLM extraction
- vector search
- online spreadsheet connectors
- GitHub/GitLab/Gitea connectors
- permissions, SSO, audit logs, multi-tenancy
- advanced AST analysis beyond Python basics
- async worker queue

## Developer Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
whywiki init-db
whywiki create "Demo Project"
whywiki ingest <PROJECT_ID> ./examples/demo-project
whywiki build <PROJECT_ID>
whywiki ask <PROJECT_ID> "这个项目当前有哪些冲突？"
whywiki serve
```

Open <http://localhost:8080>.

## Docker Setup

```bash
docker compose up --build
```

## Codex Workflow

1. Read `AGENTS.md`.
2. Read `docs/CODEX_TASKS.md`.
3. Start with one task at a time.
4. After each meaningful change, run:

```bash
python -m compileall whywiki
python -m pytest -q
```

## Product Direction

WhyWiki should feel like a local product, not a source-code demo.

The ideal flow:

```text
choose a project
  -> import materials
  -> build project memory
  -> review conflicts
  -> use the wiki, handover pack, and evidence-backed answers
```

First-board priorities:

1. Make the local project flow robust.
2. Keep the public package, command, docs, and UI aligned under `whywiki`.
3. Support `init-db`, `create`, `ingest`, `build`, `ask`, and `serve`.
4. Improve blocks and facts.
5. Improve conflict detection.
6. Improve the Web UI.
7. Add LLM calls only after deterministic behavior is stable.

WhyWiki should stay small, local-first, inspectable, and evidence-backed.
