# ProjectWiki First-Board Design

This document is the implementation-facing design for the ProjectWiki first board. It combines the product entry point, local project-memory engine, evidence-backed algorithms, Web dashboard, bilingual UI, demo requirements, and acceptance criteria.

The first board is not a generic RAG chatbot and not a documentation portal. It is a local-first project memory workspace:

```text
local files / git repo / docs / code
  -> parsers
  -> source blocks
  -> project facts
  -> conflict detection
  -> wiki pages
  -> handover pack
  -> ask with evidence
  -> bilingual Web dashboard
```

## 1. Product Positioning

ProjectWiki remembers project knowledge and why a project changed. Git remembers code changes; ProjectWiki remembers requirements, decisions, conflicts, handover context, and evidence.

Target users:

- individual developers with long-running side projects
- small teams with changing requirements
- labs and data science teams with scattered experiments
- open-source maintainers who need contributor onboarding context
- consulting or outsourced teams that need fast handover

The first board must feel like a usable local product, not a source-code demo. It should open into a Web dashboard and let users complete the full project-memory workflow without returning to the terminal.

## 2. First-Run Experience

The target public entry point is npm-first:

```bash
npm install -g projectwiki
projectwiki
```

`projectwiki` starts the local Web app quietly, initializes the data directory, uses the default local URL, and prints a clickable link:

```text
ProjectWiki is running locally.

Open:
http://127.0.0.1:8765

Logs:
projectwiki log

Data:
~/.projectwiki
```

Normal users should only need `projectwiki`. Troubleshooting users should only need `projectwiki log`.

## 3. Local App Launcher

The npm package is a launcher for the local ProjectWiki app.

Required commands:

```bash
projectwiki          # start quietly, print the local Web URL
projectwiki open     # open the current Web UI
projectwiki status   # show running state, port, version, and data directory
projectwiki log      # show logs for the current or most recent startup
projectwiki stop     # stop the local background service
projectwiki doctor   # diagnose port, runtime, and data directory problems
```

Launcher behavior:

- default host is `127.0.0.1`
- default port is `8765`
- if the port is occupied by a running ProjectWiki instance, show the current port, process id, startup information, and ask whether to continue using it or restart ProjectWiki
- if the port is occupied by another process, show the process information and ask whether to kill that process and start ProjectWiki or cancel startup
- the launcher must not choose a random fallback port automatically
- default data directory is `~/.projectwiki`
- logs are written to `~/.projectwiki/logs/projectwiki.log`
- pid and runtime metadata are written under `~/.projectwiki/run/`
- repeated `projectwiki` calls are idempotent

The launcher must not require users to understand Python virtual environments, uvicorn, Docker, process IDs, or log redirection.

## 4. System Scope

The first board must support this complete workflow:

1. Create a project.
2. Ingest a local folder, single supported file, or local Git repo.
3. Parse materials into source-backed blocks.
4. Extract project facts from blocks.
5. Detect conflicts and review items.
6. Generate wiki pages.
7. Generate a handover pack.
8. Ask questions and receive evidence-backed answers.
9. Use all of the above through the Web dashboard.

The CLI remains useful for automation and development, but product work happens in the Web UI.

## 5. Data Model

The first board should keep the existing SQLite model and strengthen it only where it improves evidence, review, or product workflow.

Core entities:

- `Project`: name, description, status, timestamps
- `Source`: project, source type, path, title, content hash, version hint, metadata
- `Block`: project, source, block type, text, location, metadata, content hash
- `Fact`: fact type, statement, evidence, confidence, status, validity status
- `Conflict`: conflict type, title, description, evidence, severity, status
- `WikiPage`: slug, title, content, updated timestamp

Evidence pointer shape:

```json
{
  "source_id": "src_xxx",
  "block_id": "blk_xxx",
  "path": "docs/requirements_latest.md",
  "location": {
    "heading": "Latest Requirements",
    "line": 12,
    "page": 3,
    "sheet": "Experiments",
    "row": 4,
    "range": "A4:E4"
  }
}
```

Every user-facing conclusion must have evidence. If evidence is missing, the UI must label the item as needing review instead of presenting it as known truth.

## 6. Ingestion Pipeline

Input sources:

- local directory
- single local file
- local Git repo
- remote Git clone as a later extension

Ingestion behavior:

- walk supported files only
- ignore `.git`, `.venv`, `node_modules`, build outputs, caches, and `.projectwiki`
- compute file content hashes
- skip unchanged sources
- update changed sources and replace their blocks
- preserve paths and parser metadata
- collect parse errors as user-visible diagnostics

Supported first-board extensions:

- `.md`, `.markdown`, `.rst`
- `.txt`
- `.csv`, `.xlsx`
- `.docx`, `.pdf`
- common code/config formats: `.py`, `.js`, `.ts`, `.tsx`, `.jsx`, `.go`, `.java`, `.rs`, `.cpp`, `.c`, `.h`, `.sh`, `.sql`, `.yaml`, `.yml`, `.json`, `.toml`, `.ini`

## 7. Parser Design

Parsers convert raw sources into blocks. They do not decide final truth.

Markdown:

- split by headings
- preserve heading, level, and section index
- fall back to plaintext chunking when no headings exist

Plaintext:

- split by paragraph chunks
- preserve chunk number

CSV:

- treat first row as headers
- each subsequent row becomes one `table_row` block
- preserve row number, headers, and values

XLSX:

- parse each worksheet
- treat first row as headers
- each subsequent row becomes one `table_row` block
- preserve sheet, row, range, headers, and values

DOCX:

- each paragraph becomes a `docx_paragraph` block
- each table row becomes a `table_row` block
- preserve paragraph number, table number, row number, and style where available

PDF:

- each page with extracted text becomes a `pdf_page` block
- preserve page number

Code:

- Python AST extracts functions, async functions, classes, and imports
- endpoint decorators are detected for FastAPI-style routes
- generic endpoint text like `POST /api/users/create` is detected with regex
- unsupported code falls back to a preview block

## 8. Fact Extraction Algorithm

First-board fact extraction is deterministic by default. LLM extraction is an optional later enhancement and must never be required for the demo.

Fact types:

- `requirement`
- `api`
- `code`
- `experiment`
- `deployment`
- `decision`
- `record`
- `document`

Classification rules:

- endpoint syntax or endpoint block -> `api`
- code symbols/imports/classes/functions -> `code`
- requirement keywords such as `Requirement`, `需求`, `用户故事` -> `requirement`
- experiment/model/data metrics such as `model`, `模型`, `experiment`, `accuracy`, `f1`, `dataset` -> `experiment`
- deployment/runtime keywords such as `deploy`, `docker`, `kubernetes`, `上线`, `部署` -> `deployment`
- decision/change-reason keywords such as `decision`, `why`, `决定`, `原因`, `废弃` -> `decision`
- table rows without stronger type -> `record`
- everything else -> `document`

Fact fields:

- statement: compact, human-readable summary
- fact type
- evidence pointer list
- confidence score
- status: `candidate`, `needs_review`, `confirmed`, or `rejected`
- validity status: `unknown`, `current`, `outdated`, or `conflicting`

Low-confidence or contradictory facts should appear in the UI as reviewable items, not as final truth.

## 9. Conflict Detection Algorithms

The first board needs conflicts that are deterministic, explainable, and visible in the demo.

### 9.1 Multiple Latest Documents

Detect multiple sources that claim to be latest/current/final.

Signals:

- file path or title contains `latest`, `final`, `current`
- Chinese signals: `最新版`, `最终版`, `当前版本`

Conflict:

- type: `multiple_latest_documents`
- severity: high
- evidence: all latest-like sources

### 9.2 Endpoint Mismatch

Detect API paths that are similar but not identical.

Signals:

- text or code contains `GET|POST|PUT|PATCH|DELETE /path`
- compare endpoints with the same method
- if path values differ but similarity is high, create a conflict

Example:

```text
POST /api/user/create
POST /api/users/create
```

Conflict:

- type: `endpoint_mismatch`
- severity: medium
- evidence: both endpoint mentions

### 9.3 Missing Mentioned Files

Detect files mentioned in docs but missing from ingested sources.

Signals:

- mentions like `scripts/start_server.sh`, `deploy.sh`, `config.yaml`, `schema.sql`
- compare basename and full path against known ingested sources
- ignore external URLs and virtualenv paths

Conflict:

- type: `missing_mentioned_file`
- severity: low or medium depending on context
- evidence: mentioning block and missing path

### 9.4 Model Architecture Mismatch

Detect conflicting model architecture terms in model/experiment/deployment contexts.

Signals:

- model context: `model`, `模型`, `architecture`, `架构`, `experiment`, `实验`
- architecture terms: `LSTM`, `Transformer`, `BERT`, `CNN`, `RNN`, `XGBoost`, `LightGBM`
- more than one active architecture term across relevant blocks

Conflict:

- type: `model_architecture_mismatch`
- severity: medium
- evidence: representative blocks for each architecture

### 9.5 Deployment Model Mismatch

Detect deployment still pointing to an old model while experiments or requirements point to a newer model.

Signals:

- deployment blocks mention `production`, `online`, `线上`, `deploy`, `部署`
- experiment or requirement blocks mention newer candidate/current model versions
- version-like terms differ, such as `model_v1.pkl` vs `v2`, or `LSTM` vs `Transformer`

Conflict:

- type: `deployment_model_mismatch`
- severity: medium or high
- evidence: deployment block plus experiment/requirement block

## 10. Wiki Generation

The wiki is generated output, not the internal source of truth.

Required pages:

- `overview`
- `requirements`
- `architecture`
- `api`
- `experiments`
- `deployment`
- `conflicts`
- `handover`
- `open-questions`

Wiki rules:

- every conclusion includes evidence
- uncertain content is labeled as uncertain
- conflicts link to evidence and review status
- pages are useful as Markdown exports
- later versions should preserve manual-edit regions instead of overwriting everything

## 11. Handover Generation

The handover pack is the first-board feature that proves ProjectWiki is more than Q&A.

Required sections:

1. Current material overview.
2. Recommended reading order.
3. Current requirements and business goals.
4. Code structure and core modules.
5. API information.
6. Experiments, models, and data.
7. Runtime and deployment.
8. Decisions and change reasons.
9. Open conflicts and review items.
10. Suggested onboarding path for a new contributor.

Every non-empty section must include evidence pointers.

## 12. Ask With Evidence

First-board Ask is deterministic evidence retrieval, not open-ended RAG.

Behavior:

- tokenize the question
- score facts by token overlap plus confidence
- score blocks by token overlap
- return top facts/blocks with evidence
- if evidence is insufficient, say so clearly
- do not invent answers outside ingested material

The response must include:

- answer text
- evidence list
- source paths
- block/fact IDs where available
- score or ranking metadata for debugging

Ask must accept Chinese and English questions. It should not require the UI language and question language to match.

## 13. Web Dashboard Design

The Web UI is the primary product surface. It should follow the Airtable/Equals-like dashboard direction documented in `docs/web_design.md`.

Core layout:

- left sidebar navigation
- top search and project switcher
- main dashboard workspace
- compact cards with thin borders
- purple primary actions
- colorful functional icons
- clear empty states

Primary navigation:

- Projects
- Project Overview
- Sources
- Facts
- Wiki
- Conflicts
- Handover
- Ask
- Settings
- Logs / Diagnostics

First-run dashboard:

- `Use demo project`
- `Create project`
- `Ingest local folder`
- project-memory explanation in one short line
- visible evidence-backed principle
- no marketing hero

Project dashboard:

- source count
- block count
- fact count
- open conflict count
- wiki page count
- latest build status
- next recommended action

## 14. Bilingual Web UI

The first-board Web UI supports Chinese and English.

Language behavior:

- detect browser language on first visit
- Chinese browser locales default to Chinese
- all other locales default to English
- provide a top-bar segmented control: `中文 | EN`
- persist the selected language in `localStorage`

Translation scope:

- sidebar labels
- buttons
- page titles
- form labels
- table columns
- empty states
- error messages
- onboarding text
- status labels
- log and diagnostics guidance

Do not automatically translate:

- ingested source content
- code
- extracted fact statements that quote source material
- wiki content generated from source text
- handover evidence excerpts
- evidence paths and locations

Rationale: translating evidence-bearing content can break traceability. The UI chrome is bilingual; project evidence remains faithful to the source.

Implementation approach:

- first board can use a lightweight dictionary such as `i18n.js`
- UI components reference translation keys
- API responses remain language-neutral structured data
- future versions can add framework-level i18n if the Web app grows

Example keys:

```text
nav.projects
nav.sources
nav.conflicts
action.ingest
action.buildWiki
empty.noProjects
error.readLogs
status.needsReview
```

## 15. Demo Project Requirements

The demo project must reliably show ProjectWiki's value in under one minute.

Required demo signals:

- at least two requirement documents claiming to be latest/final
- API mismatch between docs and code, such as `/api/user/create` vs `/api/users/create`
- missing script mentioned in docs, such as `scripts/start_server.sh`
- model architecture mismatch, such as `LSTM` vs `Transformer`
- deployment or production material pointing to an older model
- code with at least one real endpoint
- experiment table with model metrics

The demo should produce:

- 2-4 visible conflicts
- wiki pages with evidence
- a handover pack
- an Ask answer that includes evidence paths

## 16. API Surface For First Board

Keep FastAPI as the local API layer.

Required API capabilities:

- create/list/get projects
- ingest source path
- build project memory
- list sources
- list blocks for a source
- list facts
- list conflicts
- update conflict status
- list wiki pages
- fetch wiki page content
- fetch handover content
- ask with evidence
- read app status and recent logs for Web diagnostics

The current API already covers the core loop. The first-board gap is mainly source/fact/detail visibility and diagnostics.

## 17. Non-Goals

Do not build these in the first board:

- generic RAG chatbot
- vector search as a required path
- GitHub/GitLab/Gitea replacement
- Confluence/Notion replacement
- enterprise permissions
- SSO
- audit logs
- multi-tenancy
- team billing
- real-time collaboration
- graph visualization product
- online spreadsheet connectors
- deep LLM agents that rewrite project truth without review

## 18. Acceptance Criteria

Startup:

- user can install with `npm install -g projectwiki`
- user can run `projectwiki`
- the command opens or prints a local URL
- repeated starts reuse the running service
- `projectwiki log` shows current or most recent startup logs

Web:

- user can complete the first-board loop from the Web UI
- dashboard is useful without reading CLI instructions
- Chinese/English toggle works
- fixed UI text switches language
- source/evidence content is not auto-translated
- errors point to logs or actionable recovery

Project memory:

- ingest creates source records and blocks
- build creates facts with evidence
- conflict detection finds the demo conflicts
- wiki pages include evidence pointers
- handover pack is generated
- Ask answers include evidence
- Ask refuses to answer when evidence is insufficient

Demo:

- a new user can run the demo within 3 minutes after install
- the demo visibly shows conflicts, wiki, handover, and Ask with evidence
- README first screen communicates Project Memory, not document Q&A

Engineering:

- behavior is covered by focused tests
- `python -m compileall projectwiki` passes
- `python -m pytest -q` passes
- heavy optional dependencies remain lazy
- functions remain testable without FastAPI where practical

## 19. Implementation Order

Recommended implementation order:

1. Stabilize schema and add lightweight migrations.
2. Add launcher/log design support in the Python CLI, then wrap with npm launcher.
3. Expand API visibility for sources, blocks, facts, conflicts, logs, and status.
4. Improve deterministic parsers and conflict rules.
5. Improve fact status, validity, and evidence rendering.
6. Build the dashboard UI with bilingual text infrastructure.
7. Add demo-first Web flow.
8. Polish README with install command, screenshot, and demo path.

The order keeps the product demo visible while preserving the core principle: evidence-backed project memory before LLM-heavy behavior.
