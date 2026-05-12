# Git Provider Collaboration Design

This document defines the first collaboration model for WhyWiki. The goal is to make small-team collaboration work without turning WhyWiki into a hosted storage service, a user-management system, or a code-hosting platform.

WhyWiki should use Git providers for identity, repository permissions, evidence access, and memory synchronization. It should not copy user code into a WhyWiki repository.

## 1. Product Principle

WhyWiki is a project memory product, not a Git hosting product.

```text
Git remembers code changes.
WhyWiki remembers project knowledge and why the project changed.
```

Collaboration should follow this rule:

```text
Can read the WhyWiki workspace repo
  -> can enter the workspace

Can write the WhyWiki workspace repo
  -> can approve facts, resolve conflicts, and commit memory changes

Can read a linked source repo
  -> can inspect source-backed evidence and rebuild code-derived memory
```

The WhyWiki workspace repo is the collaboration boundary for project memory. Linked code and documentation repos remain on their original Git providers.

## 2. Non-Goals

The first collaboration version must not become:

- a GitHub, GitLab, or Gitea replacement
- a generic file storage system
- an enterprise identity and access management product
- a multi-tenant SaaS backend
- a repository mirror that stores all user code
- a directory-level permission system inside one WhyWiki workspace

If two projects require different readers, they should live in different WhyWiki workspace repos. One workspace repo should be treated as one permission domain.

## 3. Storage Boundaries

WhyWiki has three distinct storage layers.

### 3.1 Local Rebuildable Cache

`whywiki.db` is local cache, similar to `.venv`, `node_modules`, or an editor index.

It should be rebuilt from:

- the workspace repo memory artifacts
- linked repo metadata
- live provider reads when the user has permission
- local parser and build outputs

It must not be committed to Git.

Local-only data includes:

- `whywiki.db`
- cloned temporary checkouts
- runtime logs
- PID and server state
- embeddings and vector indexes
- LLM cache
- raw prompt/debug logs
- OAuth tokens and provider secrets
- UI session state

### 3.2 WhyWiki Workspace Repo

The workspace repo stores durable, reviewable project memory. It may be hosted on GitHub, Gitea, GitLab, or another compatible Git provider.

It should store:

- workspace configuration
- project configuration
- linked repository descriptors
- source indexes and evidence pointers
- extracted facts
- detected conflicts
- review events
- generated wiki pages
- generated handover packs
- pinned evidence-backed answers

It must not store:

- full code repo copies
- private source snapshots
- OAuth tokens
- local database files
- vector indexes
- provider API cache with private file contents

Recommended layout:

```text
whywiki.yaml
projects/
  <project-slug>/
    project.yaml
    linked-repos.yaml
    sources.jsonl
    facts.jsonl
    conflicts.jsonl
    review-events.jsonl
    wiki/
      overview.md
      requirements.md
      architecture.md
      api.md
      conflicts.md
      handover.md
    ask/
      pinned.jsonl
```

### 3.3 Linked Source Repos

Linked source repos contain the real project material:

- code
- docs
- requirements
- issue exports if the team commits them there
- experiment files
- deployment files

WhyWiki stores links, commit identifiers, paths, line ranges, hashes, and metadata. It does not store the whole repo inside the workspace.

## 4. Identity Model

WhyWiki should support logging in through external Git providers.

First-class providers:

- GitHub
- Gitea

Future providers:

- GitLab
- Forgejo
- generic OAuth plus Git HTTP API where feasible

A user may connect multiple accounts at the same time:

```yaml
connected_accounts:
  - provider: github
    account: alice
    provider_user_id: "123456"
  - provider: gitea
    base_url: https://git.company.example
    account: alice
    provider_user_id: "42"
```

Gitea identities must include `base_url`, because Gitea is often self-hosted and multiple Gitea servers may be used by one team.

Provider tokens are local secrets. They should live in the OS credential store where available, or an encrypted local credential file. They must never be written into the WhyWiki workspace repo.

## 5. Login Flow

The UI should expose provider-specific login actions:

```text
Login with GitHub
Login with Gitea
```

For Gitea, the user must first provide or select a server URL.

Login flow:

```text
User clicks Login with GitHub / Gitea
  -> WhyWiki completes the provider OAuth flow
  -> WhyWiki stores the local provider credential
  -> WhyWiki records a local connected-account identity
  -> WhyWiki checks access to the selected workspace repo
  -> WhyWiki checks access to linked source repos for visible projects
```

Login alone is not enough to enter a workspace. The user must be able to read the selected WhyWiki workspace repo.

## 6. Workspace Access Rules

Access should fail closed.

### 6.1 Enter Workspace

Required:

- authenticated provider account
- read access to the WhyWiki workspace repo

If the user cannot read the workspace repo, WhyWiki must not show workspace project names, wiki pages, conflict titles, or linked repo metadata.

### 6.2 View Project

Required:

- read access to the WhyWiki workspace repo
- read access to every required linked repo for that project, or partial-access handling if the project marks some linked repos as optional

If a user can read the workspace repo but cannot read a linked source repo, WhyWiki should show a permission-blocked state instead of leaking generated source-derived content by default.

The safer first-board behavior is:

```text
No linked source repo access
  -> hide source-derived facts, wiki pages, ask answers, and evidence snippets for that project
  -> show which provider/repo permission is missing
```

### 6.3 Review And Resolve

Required:

- read access to the WhyWiki workspace repo
- write access to the WhyWiki workspace repo
- read access to linked source repos used by the reviewed evidence

Actions:

- approve fact
- reject fact
- mark conflict resolved
- ignore conflict
- add reviewer note
- commit review event

### 6.4 Rebuild Project Memory

Required:

- read access to the WhyWiki workspace repo
- read access to linked source repos

The rebuild writes local `whywiki.db` and generated artifacts. Committing generated memory artifacts back to the workspace repo additionally requires write access to the workspace repo.

### 6.5 Modify Source Repo

Modifying code is not a first-board WhyWiki action. If future workflows propose source repo changes or open pull requests, they must require write permission on the linked source repo and should use the provider's PR flow.

## 7. Linked Repo Permission Matrix

One workspace may link to repos across providers.

Example:

```yaml
workspace:
  provider: gitea
  base_url: https://git.company.example
  repo: ai/whywiki-memory

projects:
  train-qa:
    linked_repos:
      - id: backend
        provider: gitea
        base_url: https://git.company.example
        repo: ai/CRRC-AI-QA-Server
        branch: main
      - id: docs
        provider: github
        repo: org/train-qa-docs
        branch: main
```

A user may need both a Gitea account and a GitHub account to fully open the project.

Permission check result:

```json
{
  "workspace": {
    "can_read": true,
    "can_write": true
  },
  "linked_repos": [
    {
      "id": "backend",
      "can_read": true,
      "can_write": false
    },
    {
      "id": "docs",
      "can_read": false,
      "can_write": false,
      "missing_provider_identity": "github"
    }
  ]
}
```

The UI should explain missing access in user language:

```text
This project links to a GitHub repository you cannot access yet. Connect GitHub or ask the repo owner for read access.
```

## 8. Evidence Pointers

Every user-facing conclusion must point back to original material.

Evidence pointer shape:

```json
{
  "provider": "github",
  "base_url": null,
  "repo": "owner/code-repo",
  "ref": "main",
  "commit": "abc123",
  "path": "src/api/users.py",
  "line_start": 12,
  "line_end": 40,
  "content_hash": "sha256:...",
  "source_id": "src_xxx",
  "block_id": "blk_xxx"
}
```

For Gitea:

```json
{
  "provider": "gitea",
  "base_url": "https://git.company.example",
  "repo": "team/backend",
  "commit": "def456",
  "path": "docs/deployment.md",
  "line_start": 8,
  "line_end": 22,
  "content_hash": "sha256:..."
}
```

WhyWiki should use provider URLs only when the current user is authorized to view the target repo.

## 9. LLM Access Rule

Product copy may say WhyWiki reads from a project link, but implementation must not give provider tokens directly to an LLM.

Required flow:

```text
WhyWiki connector checks provider permission
  -> fetches only the required file ranges, symbols, docs, or diffs
  -> constructs minimal evidence-backed context
  -> sends only necessary context to the LLM
  -> stores conclusions with evidence pointers
```

This keeps provider credentials inside WhyWiki and reduces the chance of source leakage.

LLM outputs must never be accepted as truth without evidence pointers.

## 10. Commit And Review Model

WhyWiki should treat workspace repo changes as reviewable Git changes.

Examples:

- approving a fact appends to `review-events.jsonl`
- resolving a conflict updates `conflicts.jsonl` or appends a review event
- rebuilding pages updates files under `wiki/`
- publishing a handover update changes `wiki/handover.md`

For write operations, first-board behavior can be:

```text
local change
  -> preview diff
  -> commit to workspace repo
  -> push to provider
```

Later versions may support pull requests for shared review:

```text
local change
  -> create branch
  -> open PR/MR in workspace repo
```

The source repo should not be modified by these actions.

## 11. Merge Strategy

Use stable IDs and append-only events wherever practical.

Recommended rules:

- `facts.jsonl` records use stable fact IDs derived from evidence and normalized statement content.
- `conflicts.jsonl` records use stable `conflict_key`.
- `review-events.jsonl` is append-only.
- generated `wiki/*.md` can be overwritten from the latest build.
- manual notes should live in explicit user-owned sections or separate files to avoid being overwritten.

The first implementation should prefer simple Git conflict visibility over hidden automatic merging. If a workspace repo has conflicts, WhyWiki should show the affected files and ask the user to resolve or pull the latest state.

## 12. UI Surfaces

Minimum first UI surfaces:

- account menu with connected GitHub and Gitea identities
- Gitea server URL manager
- workspace selector by provider/repo
- workspace permission status
- project linked repo permission status
- blocked state for missing repo access
- approve/resolve controls gated by workspace write permission
- evidence links gated by linked repo read permission

The UI should not show internal OAuth details unless the user is diagnosing access.

## 13. CLI Surfaces

Possible CLI commands:

```bash
whywiki auth login github
whywiki auth login gitea --url https://git.company.example
whywiki auth list
whywiki workspace connect <provider-repo-url>
whywiki workspace status
whywiki sync pull
whywiki sync push
whywiki rebuild <project>
```

The Web UI remains the main product surface. CLI commands exist for automation and debugging.

## 14. Security Defaults

Default security rules:

- fail closed when provider access cannot be verified
- never commit tokens or local secrets
- never commit cloned source repos
- do not expose generated source-derived content to users who cannot read the linked source repo
- do not pass provider tokens to LLM providers
- include commit SHA and content hash in evidence pointers
- show permission-blocked states rather than partial private content

## 15. First Implementation Scope

The first implementation should be small:

1. Add workspace and linked repo configuration files.
2. Add provider account records in local credential/session storage.
3. Implement GitHub and Gitea permission checks.
4. Gate workspace entry by workspace repo read permission.
5. Gate approve/resolve by workspace repo write permission.
6. Gate source-derived evidence by linked repo read permission.
7. Keep `whywiki.db` local and rebuildable.
8. Export durable memory artifacts to the workspace repo.

Do not implement enterprise roles, custom permission groups, source repo write actions, or hosted storage in the first collaboration version.

## 16. Acceptance Criteria

The design is accepted when:

- a user can connect both GitHub and Gitea accounts
- a workspace can be selected from a Git provider repo
- a user without workspace repo read access cannot enter the workspace
- a user with workspace read but no write can view allowed content but cannot approve or resolve
- a user with workspace write can approve facts and resolve conflicts
- a user without linked source repo access cannot see source-derived project memory
- `whywiki.db` is rebuilt locally and is never required for collaboration
- no code repo is copied into the WhyWiki workspace repo
- every visible conclusion has an evidence pointer to the original provider repo, commit, path, and range when available
