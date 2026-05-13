# Real Git Provider Login Design

This spec turns the current GitHub and Gitea login placeholders into real local authentication for WhyWiki.

The goal is not to build a WhyWiki account system. The goal is to let WhyWiki use the user's existing Git provider identity to check workspace and linked-repo access, while keeping provider tokens out of project memory artifacts and out of `accounts.json`.

## 1. Context

WhyWiki already has the collaboration boundary:

```text
Can read the WhyWiki workspace repo
  -> can enter the workspace

Can write the WhyWiki workspace repo
  -> can approve facts, resolve conflicts, and commit memory changes

Can read a linked source repo
  -> can inspect source-backed evidence and rebuild code-derived memory
```

The current implementation includes:

- `ProviderIdentity`, `RepoRef`, `RepoPermission`, and `WorkspaceAccessReport` in `whywiki/collaboration/models.py`
- local account metadata through `AccountStore`
- GitHub and Gitea API clients that can check repository permissions when given a token
- `/api/auth/accounts` and `/api/workspace/status`
- disabled `Login with GitHub` and `Login with Gitea` buttons in the static UI

The missing piece is real token acquisition, safe token storage, and a provider registry that can use stored local credentials instead of static test permissions.

## 2. Product Decisions

### 2.1 Identity Stays With Git Providers

WhyWiki must not introduce its own user table, password login, or hosted identity layer for the first version.

Users authenticate through:

- GitHub
- one or more Gitea servers, each identified by `base_url`

WhyWiki stores only non-sensitive connected-account metadata in `accounts.json`:

```json
{
  "connected_accounts": [
    {
      "provider": "github",
      "account": "alice",
      "provider_user_id": "123456"
    },
    {
      "provider": "gitea",
      "base_url": "https://git.company.example",
      "account": "alice",
      "provider_user_id": "42"
    }
  ]
}
```

No access token, refresh token, OAuth code, client secret, or device code may be written to this file.

### 2.2 Token Storage Is Cross-Platform And Explicit

Tokens live behind a `TokenStore` interface:

```python
class TokenStore(Protocol):
    def save(self, identity: ProviderIdentity, token: ProviderToken) -> None: ...
    def load(self, identity: ProviderIdentity) -> ProviderToken | None: ...
    def delete(self, identity: ProviderIdentity) -> None: ...
```

The preferred implementation uses the operating system credential service:

- macOS: Keychain
- Windows: Windows Credential Manager / DPAPI-backed credential storage
- Linux: Secret Service / libsecret where available

The implementation should use a small, lazy optional dependency such as `keyring` if it gives reliable access to those backends. If no system credential backend is available, WhyWiki must not silently store tokens in plaintext.

Fallback behavior:

- default: fail clearly with a user-facing message that token storage is unavailable
- explicit developer override: allow a local file token store only when `WHYWIKI_ALLOW_FILE_TOKEN_STORE=1`
- file fallback location: `get_data_dir() / "auth" / "tokens.json"`
- file fallback permissions: owner-read/write where the platform supports it
- file fallback warning: UI and logs must say that this is less safe than the OS credential store

This keeps macOS and Windows first-class while still allowing constrained development environments to proceed deliberately.

### 2.3 Stable Credential Keys

Token keys must be deterministic and must not include the token value:

```text
service: whywiki
username: github:<provider_user_id>

service: whywiki
username: gitea:<normalized_base_url>:<provider_user_id>
```

Temporary login sessions use separate short-lived state keys and are deleted after success, denial, expiry, or server restart.

### 2.4 Scopes Stay Visible

WhyWiki should request the narrowest practical permissions for the action:

- read identity
- read repository metadata and source-backed evidence
- write repository content only when the user needs to commit memory artifacts or review events back to the workspace repo

If a provider requires a broad scope for private repository checks, the UI must say so before the user authorizes. WhyWiki should not hide scope breadth behind a generic "Login" label.

The first implementation should separate "connect my identity" from "verify this private workspace". Connecting an identity can use a narrow identity scope. Verifying private repository access may require a broader provider repository scope, especially for GitHub OAuth apps, and that escalation must be shown as a deliberate authorization step.

## 3. Provider Flows

### 3.1 GitHub

Use GitHub OAuth Device Flow for the local-first application.

Why this fits:

- local app does not need to expose a public callback
- no client secret is embedded in the open-source repo
- the user can authorize in the browser and return to WhyWiki

Configuration:

- require a GitHub OAuth app client id through `WHYWIKI_GITHUB_CLIENT_ID` or a local settings file
- show a setup error if the client id is missing
- do not store or require a GitHub client secret

Flow:

```text
User clicks Login with GitHub
  -> POST /api/auth/github/device/start
  -> WhyWiki calls GitHub device-code endpoint
  -> UI shows verification URL, user code, expiry, and polling status
  -> User authorizes in GitHub
  -> UI polls /api/auth/github/device/poll
  -> WhyWiki exchanges the device code for an access token
  -> WhyWiki calls GitHub /user to get account identity
  -> WhyWiki stores token in TokenStore
  -> WhyWiki stores ProviderIdentity in AccountStore
  -> WhyWiki reloads /api/auth/accounts and /api/workspace/status
```

Token polling must respect the provider interval and handle pending, slow-down, denied, and expired states without spamming the provider.

### 3.2 Gitea

Use OAuth2 Authorization Code with PKCE.

Why this fits:

- Gitea supports self-hosted servers, so `base_url` is part of the identity
- PKCE avoids storing a client secret in WhyWiki
- the local callback can return to the running FastAPI app

Configuration:

- user enters or selects a Gitea `base_url`
- user provides a client id registered on that Gitea instance
- redirect URI is `http://127.0.0.1:8765/api/auth/gitea/callback`
- the Gitea OAuth application must be configured as a public client for PKCE

Flow:

```text
User clicks Login with Gitea
  -> UI asks for base_url and client_id when missing
  -> POST /api/auth/gitea/start
  -> WhyWiki creates state, code_verifier, and code_challenge
  -> UI opens the returned authorization URL
  -> Gitea redirects back to /api/auth/gitea/callback
  -> WhyWiki validates state and exchanges code plus verifier for token
  -> WhyWiki calls Gitea user endpoint or userinfo endpoint to get identity
  -> WhyWiki stores token in TokenStore
  -> WhyWiki stores ProviderIdentity in AccountStore
  -> WhyWiki reloads /api/auth/accounts and /api/workspace/status
```

The callback page should show a short success or failure state and point the user back to the WhyWiki tab.

## 4. Backend API Surface

Add provider auth endpoints without changing the existing workspace API shape.

```text
GET    /api/auth/accounts
DELETE /api/auth/accounts/{identity_key}

POST   /api/auth/github/device/start
POST   /api/auth/github/device/poll

POST   /api/auth/gitea/start
GET    /api/auth/gitea/callback
```

`identity_key` is the URL-safe form of the credential key, not a token. It must include enough information to distinguish multiple Gitea servers:

```text
github:<provider_user_id>
gitea:<normalized_base_url>:<provider_user_id>
```

Response shape should keep the UI state-oriented:

```json
{
  "status": "waiting_for_user",
  "provider": "github",
  "verification_uri": "https://github.com/login/device",
  "user_code": "ABCD-1234",
  "expires_in": 900,
  "poll_after_seconds": 5
}
```

Errors must be actionable:

- missing client id
- provider denied authorization
- device code expired
- callback state mismatch
- token store unavailable
- insufficient token scope
- provider API unavailable
- workspace repo unreadable

No endpoint should return token values.

## 5. Provider Registry Integration

Replace static-only provider registration with layered registration:

```text
stored token identities
  -> real GitHubProviderClient / GiteaProviderClient

WHYWIKI_COLLAB_STATIC_PERMISSIONS
  -> StaticProviderClient only for tests and explicit local demos
```

Runtime behavior:

- `/api/workspace/status` uses real provider clients when matching tokens exist
- if an identity exists but token loading fails, report a token-storage error state without leaking secrets
- if no identity exists for the provider key, keep the current fail-closed behavior

The existing `GitHubProviderClient` and `GiteaProviderClient` are reused for repository permission checks. They may need small extensions for authenticated user lookup and token-scope checks, but repo permission logic should remain centralized.

## 6. UI / UX Design

The login UI must reduce uncertainty rather than only enabling two buttons.

Primary user goals:

- connect a Git provider account
- understand whether the account can enter the configured workspace
- understand whether linked source repos are readable
- understand when a broader provider scope is being requested

States to show:

- not connected
- setup needed
- waiting for authorization
- connected
- token storage unavailable
- authorization denied or expired
- workspace access denied
- workspace read-only
- missing linked repo access

Button labels should describe results:

- `Connect GitHub account`
- `Connect Gitea account`
- `Open GitHub authorization`
- `Retry authorization`
- `Disconnect account`

For GitHub device flow, the UI shows the verification URL and user code in a focused panel, with polling progress and expiry. For Gitea PKCE, the UI shows base URL and client id inputs only when needed, then opens the provider authorization URL.

The sidebar status pill can continue summarizing connected accounts, but detailed setup, errors, and next steps should live in the Settings view or a dedicated connection panel. This avoids forcing all auth complexity into the narrow sidebar.

## 7. Security Rules

- Never write tokens to `accounts.json`.
- Never write tokens to the WhyWiki workspace repo.
- Never log access tokens, refresh tokens, OAuth codes, device codes, client secrets, or PKCE verifiers.
- Use `state` for every redirect-style flow.
- Use PKCE for Gitea public-client login.
- Delete temporary auth sessions after completion or expiry.
- Keep token fallback visible and opt-in.
- Fail closed when provider identity or repository permission is missing.
- Treat token scopes as part of the user-facing permission state.

## 8. Tests And Verification

Backend tests:

- account metadata still strips token-like fields
- token store key generation is stable for GitHub and multiple Gitea servers
- token store never serializes secrets into `accounts.json`
- file token fallback requires `WHYWIKI_ALLOW_FILE_TOKEN_STORE=1`
- GitHub device start and poll handle pending, slow-down, success, denial, and expiry with mocked HTTP
- Gitea PKCE start creates state and code challenge; callback rejects state mismatch
- callback success saves identity metadata and token through the token store abstraction
- provider registry uses stored tokens to register real provider clients
- `/api/workspace/status` remains fail-closed when token loading fails

Frontend tests:

- login placeholders are no longer disabled once auth config is available
- setup-needed state appears when GitHub client id or Gitea client id is missing
- GitHub device-code panel renders code, verification URL, expiry, polling, and errors
- Gitea setup panel renders base URL, client id, redirect guidance, and errors
- connected account status does not expose token values

Manual verification:

```bash
python -m compileall whywiki
python -m pytest -q
./start.sh
```

Then verify in the browser:

- GitHub login reaches device authorization and returns a connected account
- Gitea login reaches the configured server authorization page and returns a connected account
- `/api/auth/accounts` shows only identity metadata
- `/api/workspace/status` reflects real provider repo permissions
- no token-like value appears in `accounts.json`, logs, or the workspace artifacts

## 9. Implementation Boundaries

This feature includes:

- real auth endpoints
- token store abstraction
- system credential backend
- explicit file fallback backend
- provider identity discovery
- workspace status integration
- minimal UI connection flow
- tests and documentation updates

This feature does not include:

- GitHub App installation flow
- GitLab support
- creating provider OAuth applications for the user
- hosted WhyWiki account login
- full workspace repo push/pull synchronization
- editing linked source repositories
- enterprise SSO

Those can be added later without changing the core rule: Git providers own identity, WhyWiki owns local project memory behavior, and provider tokens remain local secrets.

## 10. External References

- GitHub OAuth app authorization and device flow: https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/authorizing-oauth-apps
- GitHub authenticated user API: https://docs.github.com/en/rest/users/users
- GitHub repository API permission payloads: https://docs.github.com/en/rest/repos/repos
- Gitea OAuth2 provider and PKCE: https://docs.gitea.com/development/oauth2-provider
- Gitea API token/authentication behavior: https://docs.gitea.com/development/api-usage
