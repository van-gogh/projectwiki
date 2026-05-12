# WhyWiki Web UX P0/P1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the current WhyWiki Web UI explain project state, next action, evidence, AI inference, conflicts, and review work without changing the backend contract.

**Architecture:** Keep the vanilla FastAPI static frontend. Add small DOM helper components in `whywiki/static/app.js`, product tokens in `whywiki/static/styles.css`, and Chinese/English UX copy in `whywiki/static/i18n.js`. Derive workflow state from existing `sources`, `facts`, `conflicts`, and `wiki_pages` endpoints.

**Tech Stack:** FastAPI static files, vanilla JavaScript, CSS, existing pytest static asset tests.

---

### Task 1: Protect P0/P1 UX Promises With Static Tests

**Files:**
- Modify: `tests/test_web_assets.py`

- [ ] Add tests asserting the frontend exposes project status hero, next action, empty states, operation feedback, evidence badges, fact cards, conflict cards, wiki reader, evidence viewer, and action-state helpers.
- [ ] Add tests asserting both i18n dictionaries contain the new user-facing copy keys.
- [ ] Add tests asserting CSS contains semantic color tokens, badge classes, focus/disabled states, empty states, operation states, and evidence drawer styles.
- [ ] Run `python -m pytest tests/test_web_assets.py -q` and confirm the new tests fail before implementation.

### Task 2: Build P0 Workflow State and Dashboard Guidance

**Files:**
- Modify: `whywiki/static/app.js`
- Modify: `whywiki/static/i18n.js`
- Modify: `whywiki/static/styles.css`

- [ ] Add helpers to derive project metrics, stage, next action, and evidence confidence from existing endpoint data.
- [ ] Replace the status page top area with a `ProjectStatusHero`, `OnboardingSteps`, `NextActionPanel`, and clearer metrics.
- [ ] Add task-specific empty states for no source, no facts, no wiki, no conflicts, no evidence, no search result, and no handover.
- [ ] Add operation feedback for ingest, build, and ask loading/success/error states.

### Task 3: Add Evidence, AI, Conflict, and Review Visual Language

**Files:**
- Modify: `whywiki/static/app.js`
- Modify: `whywiki/static/i18n.js`
- Modify: `whywiki/static/styles.css`

- [ ] Add `StatusBadge`, `SourceBadge`, `EvidenceBadge`, and confidence labels.
- [ ] Render facts with source type, confidence, evidence, AI inference/candidate, needs review, confirmed, and conflict states.
- [ ] Render conflicts as review cards with severity, affected evidence paths, and resolve/ignore actions wired to the existing PATCH API.
- [ ] Add an evidence drawer/panel that shows original paths and location metadata without dumping raw JSON by default.

### Task 4: Improve P1 Page Hierarchy and Interaction States

**Files:**
- Modify: `whywiki/static/app.js`
- Modify: `whywiki/static/i18n.js`
- Modify: `whywiki/static/styles.css`

- [ ] Upgrade Wiki from record grid plus pre block to page index plus reader.
- [ ] Upgrade Ask to show answer, evidence list, no-evidence recovery copy, loading, and error state.
- [ ] Upgrade Settings to diagnostics/settings language and move handover into a clearer secondary export card.
- [ ] Add hover, focus, active, disabled, primary, secondary, tertiary, destructive, and AI action styling.

### Task 5: Verify

**Files:**
- No production edits unless verification reveals a defect.

- [ ] Run `python -m compileall whywiki`.
- [ ] Run `python -m pytest -q`.
- [ ] Start or reuse the local app and verify the main pages visually if the environment allows.
