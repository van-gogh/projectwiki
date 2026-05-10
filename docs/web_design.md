# ProjectWiki Web and Startup Design

ProjectWiki should feel like a local product, not a source-code demo. The first-run experience should lead users into the Web dashboard with one command, then keep all normal work inside the browser.

## Startup Experience

Target first-board product flow:

```bash
npm install -g projectwiki
projectwiki
```

The `projectwiki` command starts the local Web server quietly, chooses an available localhost port if needed, initializes the data directory, and prints a clickable link:

```text
ProjectWiki is running locally.

Open:
http://127.0.0.1:8765

Logs:
projectwiki log

Data:
~/.projectwiki
```

The command should be idempotent. If ProjectWiki is already running, it should not start a second server; it should show the existing URL and current status.

## Launcher Commands

The npm package should expose a small local-app launcher:

```bash
projectwiki          # start quietly, print the local Web URL
projectwiki open     # open the current Web UI
projectwiki status   # show running state, port, version, and data directory
projectwiki log      # show logs for the current or most recent startup
projectwiki stop     # stop the local background service
projectwiki doctor   # diagnose port, runtime, and data directory problems
```

`projectwiki log` is part of the product surface. Users should not need to know process IDs, Docker logs, uvicorn internals, or where stdout was redirected. The first version can read from `~/.projectwiki/logs/projectwiki.log` and support a simple `--tail` option later.

## Installation Strategy

Use npm as the first public install path because it matches modern CLI product expectations and avoids asking users to clone the repository.

Phase 1:

- Publish a lightweight npm launcher package.
- The launcher starts the local Python/FastAPI server using the installed project runtime.
- Python, Docker, and source checkout remain developer setup paths.

Phase 2:

- Move toward standalone platform artifacts downloaded by the npm launcher.
- Users should not need to understand Python virtual environments, pip, uvicorn, or Docker.

## Web UI Direction

The Web UI should be a dashboard-style workspace, similar in density and tone to Airtable/Equals rather than a landing page.

Reference:

```bash
npx getdesign@latest add airtable
```

Use that family of visual choices as guidance:

- left sidebar navigation
- top search bar
- light neutral background
- thin borders
- compact cards with small radius
- restrained shadows
- purple primary action
- colorful functional icons
- clear empty states
- SaaS dashboard typography

Avoid a marketing hero as the first screen. The first screen should be the actual product workspace.

## Dashboard Structure

Primary layout:

- Sidebar: Projects, Sources, Wiki, Conflicts, Handover, Ask, Settings
- Top bar: project switcher, search, status, local server indicator
- Main dashboard: getting-started card, project health, recent sources, conflict summary, wiki pages, handover shortcut
- Floating help/log affordance: links to `projectwiki log` and diagnostics when startup or ingest fails

First-run dashboard:

- prominent `Use demo project` action
- `Create project` action
- `Ingest local folder` action
- visible explanation that all conclusions are evidence-backed
- no large text-only onboarding page

## Product Principle

The CLI starts and maintains the local app. The Web UI is where users work.

Normal users should only need:

```bash
projectwiki
```

Troubleshooting users should only need:

```bash
projectwiki log
```
