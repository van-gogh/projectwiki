# AGENTS.md

This repository is designed to be developed with Codex or similar agentic coding tools.

## Product direction

Build an open-source WhyWiki for small teams, labs, open-source projects, and messy software projects.

Do not turn it into:

- a generic RAG chatbot
- a GitHub/GitLab/Gitea replacement
- a Confluence/Notion/Feishu replacement
- an enterprise suite in the first version
- a graph visualization product

Core principle:

```text
Git remembers code changes.
WhyWiki remembers project knowledge and why the project changed.
```

## Current architecture

```text
local files / git repo / docs / code
  -> parsers
  -> source blocks
  -> deterministic or LLM-assisted facts
  -> conflicts, wiki pages, handover, ask
```

Markdown is a rendered output. Preserve evidence pointers to original files, pages, sheets, ranges, or code symbols.

## Coding standards

- Prefer small modules with clear boundaries.
- Avoid hidden global state except the configured data directory.
- Keep functions testable without FastAPI.
- Every user-facing conclusion should have an evidence pointer.
- Avoid overengineering enterprise features.
- Add tests when adding behavior.
- Use type hints where practical.
- Keep optional heavy dependencies imported lazily.

## Test commands

Run after each meaningful change:

```bash
python -m compileall whywiki
python -m pytest -q
```

## First-board priorities

1. Make the local project flow robust.
2. Support `whywiki init-db`, `create`, `ingest`, `build`, `ask`, `serve`.
3. Improve blocks and facts.
4. Improve conflict detection.
5. Improve Web UI.
6. Add LLM calls only after deterministic behavior is stable.
