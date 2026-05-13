# Real Git Provider Login Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the disabled GitHub and Gitea login shell with real local provider authentication, cross-platform token storage, and token-backed workspace permission checks.

**Architecture:** Keep WhyWiki local-first: provider identity remains in GitHub/Gitea, `accounts.json` stores only non-sensitive metadata, and tokens live behind a `TokenStore` backed by the OS credential service or an explicit local file fallback. OAuth/device-flow code is isolated from FastAPI route wiring, and workspace access continues through `ProviderRegistry` plus `CollaborationService`.

**Tech Stack:** Python 3.10+, FastAPI, stdlib `urllib`, optional `keyring` package for macOS Keychain / Windows Credential Manager / Linux Secret Service, static HTML/CSS/JS, pytest.

---

## File Structure

- Modify `pyproject.toml`
  - Add `keyring>=25.0` as a normal dependency because real login is a core product path and the app must work on macOS/Windows without manual extra installation.
- Modify `whywiki/collaboration/models.py`
  - Add `ProviderIdentity.identity_key`.
- Modify `whywiki/collaboration/accounts.py`
  - Add `delete_identity(identity_key: str)`.
- Create `whywiki/collaboration/tokens.py`
  - Own `ProviderToken`, `TokenStore`, `KeyringTokenStore`, `FileTokenStore`, fallback selection, stable credential keys, and secret-safe serialization.
- Create `whywiki/collaboration/oauth.py`
  - Own GitHub device flow, Gitea PKCE flow, temporary auth session storage, and provider identity lookup.
- Create `whywiki/collaboration/registry.py`
  - Build a `ProviderRegistry` from account metadata, token storage, and static demo permissions.
- Modify `whywiki/collaboration/providers.py`
  - Add authenticated-user lookup helpers on real provider clients.
- Modify `whywiki/app.py`
  - Add auth request models, token/auth stores, auth endpoints, and switch workspace status to token-backed registry construction.
- Modify `whywiki/static/index.html`
  - Enable provider buttons and add a settings auth panel target.
- Modify `whywiki/static/app.js`
  - Add GitHub device flow UI, Gitea PKCE start UI, account disconnect, auth status rendering, and workspace refresh.
- Modify `whywiki/static/i18n.js`
  - Add English and Chinese auth setup/status copy.
- Modify `whywiki/static/styles.css`
  - Add focused auth panel, code display, warning, and loading styles.
- Modify `docs/FEATURE_STATUS.md` and `README.md`
  - Mark real Git provider login as implemented and document configuration.
- Add tests:
  - `tests/test_provider_tokens.py`
  - `tests/test_provider_oauth.py`
  - `tests/test_auth_api.py`
  - Update `tests/test_provider_accounts.py`
  - Update `tests/test_provider_permissions.py`
  - Update `tests/test_collaboration_api.py`
  - Update `tests/test_web_assets.py`

## UX Plan Before UI Code

User goal: connect a Git provider account and understand whether that account can enter the configured WhyWiki workspace.

Primary action: `Connect GitHub account` or `Connect Gitea account`.

Current status: show one of `Not connected`, `Setup needed`, `Waiting for authorization`, `Connected`, `Token storage unavailable`, `No workspace access`, `Workspace read-only`, or `Missing linked repo access`.

Next step: every failure state must include one action: configure client id, open provider authorization, retry authorization, disconnect account, or inspect workspace permission.

Evidence/security distinction: account names are metadata; token values never render in the UI, API response, logs, `accounts.json`, or workspace artifacts.

---

### Task 1: Token Storage And Identity Keys

**Files:**
- Modify: `pyproject.toml`
- Modify: `whywiki/collaboration/models.py`
- Modify: `whywiki/collaboration/accounts.py`
- Create: `whywiki/collaboration/tokens.py`
- Test: `tests/test_provider_tokens.py`
- Test: `tests/test_provider_accounts.py`

- [ ] **Step 1: Write failing token and identity tests**

Add `tests/test_provider_tokens.py`:

```python
import json
import stat

import pytest

from whywiki.collaboration.models import ProviderIdentity
from whywiki.collaboration.tokens import (
    FileTokenStore,
    ProviderToken,
    TokenStoreUnavailable,
    default_token_store,
    token_store_key,
)


def test_token_store_key_is_stable_for_github():
    identity = ProviderIdentity(provider="github", account="alice", provider_user_id="123")

    assert identity.identity_key == "github:123"
    assert token_store_key(identity) == ("whywiki", "github:123")


def test_token_store_key_distinguishes_gitea_servers():
    first = ProviderIdentity(
        provider="gitea",
        account="alice",
        provider_user_id="42",
        base_url="https://git.one.test/",
    )
    second = ProviderIdentity(
        provider="gitea",
        account="alice",
        provider_user_id="42",
        base_url="https://git.two.test",
    )

    assert first.identity_key == "gitea:https://git.one.test:42"
    assert second.identity_key == "gitea:https://git.two.test:42"
    assert token_store_key(first) != token_store_key(second)


def test_file_token_store_requires_explicit_opt_in(tmp_path, monkeypatch):
    monkeypatch.delenv("WHYWIKI_ALLOW_FILE_TOKEN_STORE", raising=False)

    with pytest.raises(TokenStoreUnavailable):
        FileTokenStore.from_env(tmp_path / "auth" / "tokens.json")


def test_file_token_store_round_trip_with_owner_only_permissions(tmp_path, monkeypatch):
    monkeypatch.setenv("WHYWIKI_ALLOW_FILE_TOKEN_STORE", "1")
    store = FileTokenStore.from_env(tmp_path / "auth" / "tokens.json")
    identity = ProviderIdentity(provider="github", account="alice", provider_user_id="123")
    token = ProviderToken(access_token="github-token", token_type="bearer", scope="repo read:user")

    store.save(identity, token)

    assert store.load(identity) == token
    payload = json.loads((tmp_path / "auth" / "tokens.json").read_text(encoding="utf-8"))
    assert payload["github:123"]["access_token"] == "github-token"
    mode = stat.S_IMODE((tmp_path / "auth" / "tokens.json").stat().st_mode)
    assert mode & stat.S_IRWXG == 0
    assert mode & stat.S_IRWXO == 0


def test_default_token_store_uses_file_fallback_only_when_enabled(tmp_path, monkeypatch):
    monkeypatch.setenv("WHYWIKI_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("WHYWIKI_ALLOW_FILE_TOKEN_STORE", "1")
    monkeypatch.setattr("whywiki.collaboration.tokens.KeyringTokenStore.available", staticmethod(lambda: False))

    store = default_token_store()

    assert isinstance(store, FileTokenStore)
```

Append to `tests/test_provider_accounts.py`:

```python
def test_account_store_deletes_identity_by_identity_key(tmp_path):
    store = AccountStore(tmp_path / "auth" / "accounts.json")
    github = ProviderIdentity(provider="github", account="alice", provider_user_id="1")
    gitea = ProviderIdentity(
        provider="gitea",
        account="alice",
        provider_user_id="1",
        base_url="https://git.example.test",
    )
    store.save_identity(github)
    store.save_identity(gitea)

    assert store.delete_identity("github:1") is True

    assert store.list_identities() == [gitea]
    assert store.delete_identity("github:missing") is False
```

- [ ] **Step 2: Run token tests and verify they fail**

Run:

```bash
.venv/bin/python -m pytest tests/test_provider_tokens.py tests/test_provider_accounts.py -q
```

Expected: failures for missing `whywiki.collaboration.tokens`, missing `ProviderIdentity.identity_key`, and missing `AccountStore.delete_identity`.

- [ ] **Step 3: Add the token dependency**

In `pyproject.toml`, add `keyring` to `[project].dependencies`:

```toml
    "pypdf>=4.2.0",
    "keyring>=25.0"
```

Keep the `dev` optional dependency group unchanged.

- [ ] **Step 4: Add `ProviderIdentity.identity_key`**

In `whywiki/collaboration/models.py`, add this property to `ProviderIdentity`:

```python
    @property
    def identity_key(self) -> str:
        if self.provider == "github":
            return f"github:{self.provider_user_id}"
        return f"gitea:{self.base_url}:{self.provider_user_id}"
```

- [ ] **Step 5: Add account deletion**

In `whywiki/collaboration/accounts.py`, add this method to `AccountStore`:

```python
    def delete_identity(self, identity_key: str) -> bool:
        identities = self.list_identities()
        kept = [identity for identity in identities if identity.identity_key != identity_key]
        if len(kept) == len(identities):
            return False
        write_json(
            self.path,
            {_CONNECTED_ACCOUNTS_KEY: [identity.to_dict() for identity in kept]},
        )
        return True
```

- [ ] **Step 6: Create `tokens.py`**

Create `whywiki/collaboration/tokens.py`:

```python
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from whywiki.config import get_data_dir
from whywiki.collaboration.models import ProviderIdentity

_SERVICE_NAME = "whywiki"
_FILE_FALLBACK_ENV = "WHYWIKI_ALLOW_FILE_TOKEN_STORE"


class TokenStoreUnavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class ProviderToken:
    access_token: str
    token_type: str = "bearer"
    scope: str = ""

    def to_json(self) -> str:
        return json.dumps(
            {
                "access_token": self.access_token,
                "token_type": self.token_type,
                "scope": self.scope,
            },
            sort_keys=True,
        )

    @classmethod
    def from_json(cls, value: str) -> ProviderToken:
        payload = json.loads(value)
        return cls(
            access_token=payload["access_token"],
            token_type=payload.get("token_type", "bearer"),
            scope=payload.get("scope", ""),
        )


class TokenStore(Protocol):
    def save(self, identity: ProviderIdentity, token: ProviderToken) -> None:
        raise NotImplementedError

    def load(self, identity: ProviderIdentity) -> ProviderToken | None:
        raise NotImplementedError

    def delete(self, identity: ProviderIdentity) -> None:
        raise NotImplementedError


def token_store_key(identity: ProviderIdentity) -> tuple[str, str]:
    return (_SERVICE_NAME, identity.identity_key)


class KeyringTokenStore:
    @staticmethod
    def available() -> bool:
        try:
            import keyring
            from keyring.errors import NoKeyringError

            backend = keyring.get_keyring()
            return backend is not None and not isinstance(backend, NoKeyringError)
        except Exception:
            return False

    def __init__(self) -> None:
        if not self.available():
            raise TokenStoreUnavailable("OS credential storage is unavailable.")

    def save(self, identity: ProviderIdentity, token: ProviderToken) -> None:
        import keyring

        service, username = token_store_key(identity)
        keyring.set_password(service, username, token.to_json())

    def load(self, identity: ProviderIdentity) -> ProviderToken | None:
        import keyring

        service, username = token_store_key(identity)
        value = keyring.get_password(service, username)
        if value is None:
            return None
        return ProviderToken.from_json(value)

    def delete(self, identity: ProviderIdentity) -> None:
        import keyring
        from keyring.errors import PasswordDeleteError

        service, username = token_store_key(identity)
        try:
            keyring.delete_password(service, username)
        except PasswordDeleteError:
            return


class FileTokenStore:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    @classmethod
    def from_env(cls, path: Path) -> FileTokenStore:
        if os.getenv(_FILE_FALLBACK_ENV) != "1":
            raise TokenStoreUnavailable(
                "Token storage is unavailable. Enable the local file fallback with WHYWIKI_ALLOW_FILE_TOKEN_STORE=1."
            )
        return cls(path)

    def _read(self) -> dict[str, dict[str, str]]:
        if not self.path.exists():
            return {}
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("token store must contain a JSON object")
        return payload

    def _write(self, payload: dict[str, dict[str, str]]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        try:
            self.path.chmod(0o600)
        except OSError:
            return

    def save(self, identity: ProviderIdentity, token: ProviderToken) -> None:
        payload = self._read()
        payload[identity.identity_key] = {
            "access_token": token.access_token,
            "token_type": token.token_type,
            "scope": token.scope,
        }
        self._write(payload)

    def load(self, identity: ProviderIdentity) -> ProviderToken | None:
        row = self._read().get(identity.identity_key)
        if row is None:
            return None
        return ProviderToken(
            access_token=row["access_token"],
            token_type=row.get("token_type", "bearer"),
            scope=row.get("scope", ""),
        )

    def delete(self, identity: ProviderIdentity) -> None:
        payload = self._read()
        payload.pop(identity.identity_key, None)
        self._write(payload)


def default_token_store() -> TokenStore:
    if KeyringTokenStore.available():
        return KeyringTokenStore()
    return FileTokenStore.from_env(get_data_dir() / "auth" / "tokens.json")
```

- [ ] **Step 7: Run token tests and commit**

Run:

```bash
.venv/bin/python -m pytest tests/test_provider_tokens.py tests/test_provider_accounts.py -q
```

Expected: all selected tests pass.

Commit:

```bash
git add pyproject.toml whywiki/collaboration/models.py whywiki/collaboration/accounts.py whywiki/collaboration/tokens.py tests/test_provider_tokens.py tests/test_provider_accounts.py
git commit -m "feat: add provider token storage"
```

---

### Task 2: OAuth Clients And Temporary Auth Sessions

**Files:**
- Create: `whywiki/collaboration/oauth.py`
- Modify: `whywiki/collaboration/providers.py`
- Test: `tests/test_provider_oauth.py`
- Test: `tests/test_provider_permissions.py`

- [ ] **Step 1: Write failing OAuth client tests**

Create `tests/test_provider_oauth.py`:

```python
import json

import pytest

from whywiki.collaboration.oauth import (
    AuthSessionStore,
    GiteaOAuthClient,
    GitHubDeviceFlowClient,
    build_pkce_challenge,
)
from whywiki.collaboration.tokens import ProviderToken


class _Response:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


def _request_header(request, name):
    for header_name, value in request.header_items():
        if header_name.lower() == name.lower():
            return value
    return None


def test_auth_session_store_consumes_sessions_once():
    store = AuthSessionStore()
    store.save("state-1", {"provider": "gitea", "code_verifier": "abc"})

    assert store.pop("state-1") == {"provider": "gitea", "code_verifier": "abc"}
    assert store.pop("state-1") is None


def test_pkce_challenge_is_urlsafe_and_without_padding():
    challenge = build_pkce_challenge("a" * 64)

    assert "=" not in challenge
    assert "/" not in challenge
    assert "+" not in challenge


def test_github_device_start_uses_json_accept_header(monkeypatch):
    captured = []

    def fake_urlopen(request, timeout):
        captured.append(request)
        return _Response(
            {
                "device_code": "device-1",
                "user_code": "ABCD-1234",
                "verification_uri": "https://github.com/login/device",
                "expires_in": 900,
                "interval": 5,
            }
        )

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    result = GitHubDeviceFlowClient("client-id").start()

    assert result["status"] == "waiting_for_user"
    assert result["device_code"] == "device-1"
    assert _request_header(captured[0], "Accept") == "application/json"


def test_github_device_poll_maps_pending_and_success(monkeypatch):
    responses = [
        _Response({"error": "authorization_pending"}),
        _Response({"access_token": "gho_token", "token_type": "bearer", "scope": "repo"}),
    ]

    def fake_urlopen(request, timeout):
        return responses.pop(0)

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    client = GitHubDeviceFlowClient("client-id")

    assert client.poll("device-1")["status"] == "waiting_for_user"
    assert client.poll("device-1")["token"] == ProviderToken("gho_token", "bearer", "repo")


def test_gitea_start_returns_authorization_url_and_session():
    client = GiteaOAuthClient("https://git.example.test", "client-id", "http://127.0.0.1:8765/callback")

    result = client.start()

    assert result["status"] == "redirect"
    assert result["authorization_url"].startswith("https://git.example.test/login/oauth/authorize?")
    assert result["session"]["provider"] == "gitea"
    assert result["session"]["base_url"] == "https://git.example.test"
    assert len(result["session"]["code_verifier"]) >= 43


def test_gitea_callback_exchanges_code_for_token(monkeypatch):
    captured = []

    def fake_urlopen(request, timeout):
        captured.append(request)
        return _Response({"access_token": "gitea-token", "token_type": "bearer", "scope": "read:repository read:user"})

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    client = GiteaOAuthClient("https://git.example.test", "client-id", "http://127.0.0.1:8765/callback")

    token = client.exchange_code("code-1", "verifier-1")

    assert token == ProviderToken("gitea-token", "bearer", "read:repository read:user")
    assert _request_header(captured[0], "Accept") == "application/json"
```

Append to `tests/test_provider_permissions.py`:

```python
from whywiki.collaboration.models import ProviderIdentity


def test_github_client_reads_authenticated_identity(monkeypatch):
    def fake_urlopen(request, timeout):
        return _FakeHTTPResponse({"login": "alice", "id": 123})

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    identity = GitHubProviderClient(token="github-token").authenticated_identity()

    assert identity.account == "alice"
    assert identity.provider_user_id == "123"
    assert identity.provider == "github"


def test_gitea_client_reads_authenticated_identity(monkeypatch):
    def fake_urlopen(request, timeout):
        return _FakeHTTPResponse({"login": "alice", "id": 42})

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    identity = GiteaProviderClient(base_url="https://git.example.test", token="gitea-token").authenticated_identity()

    assert identity.account == "alice"
    assert identity.provider_user_id == "42"
    assert identity.base_url == "https://git.example.test"
```

- [ ] **Step 2: Run OAuth tests and verify they fail**

Run:

```bash
.venv/bin/python -m pytest tests/test_provider_oauth.py tests/test_provider_permissions.py -q
```

Expected: failures for missing `oauth.py`, `authenticated_identity`, and OAuth client classes.

- [ ] **Step 3: Create OAuth helpers**

Create `whywiki/collaboration/oauth.py`:

```python
from __future__ import annotations

import base64
import hashlib
import json
import secrets
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from whywiki.collaboration.tokens import ProviderToken


def _post_form(url: str, data: dict[str, str], timeout: float) -> dict:
    request = Request(
        url,
        data=urlencode(data).encode("utf-8"),
        headers={
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "WhyWiki",
        },
        method="POST",
    )
    with urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def build_pkce_challenge(code_verifier: str) -> str:
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def new_code_verifier() -> str:
    return secrets.token_urlsafe(64)[:128]


class AuthSessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, dict[str, str]] = {}

    def save(self, state: str, payload: dict[str, str]) -> None:
        self._sessions[state] = dict(payload)

    def pop(self, state: str) -> dict[str, str] | None:
        return self._sessions.pop(state, None)


class GitHubDeviceFlowClient:
    def __init__(self, client_id: str, timeout: float = 10.0) -> None:
        self.client_id = client_id
        self.timeout = timeout

    def start(self) -> dict:
        payload = _post_form(
            "https://github.com/login/device/code",
            {"client_id": self.client_id, "scope": "repo read:user"},
            self.timeout,
        )
        return {
            "status": "waiting_for_user",
            "provider": "github",
            "device_code": payload["device_code"],
            "user_code": payload["user_code"],
            "verification_uri": payload["verification_uri"],
            "expires_in": payload.get("expires_in", 900),
            "poll_after_seconds": payload.get("interval", 5),
        }

    def poll(self, device_code: str) -> dict:
        payload = _post_form(
            "https://github.com/login/oauth/access_token",
            {
                "client_id": self.client_id,
                "device_code": device_code,
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
            },
            self.timeout,
        )
        error = payload.get("error")
        if error in {"authorization_pending", "slow_down"}:
            return {
                "status": "waiting_for_user",
                "provider": "github",
                "error": error,
                "poll_after_seconds": payload.get("interval", 5),
            }
        if error in {"expired_token", "access_denied"}:
            return {"status": "failed", "provider": "github", "error": error}
        if error:
            return {"status": "failed", "provider": "github", "error": error}
        return {
            "status": "authorized",
            "provider": "github",
            "token": ProviderToken(
                access_token=payload["access_token"],
                token_type=payload.get("token_type", "bearer"),
                scope=payload.get("scope", ""),
            ),
        }


class GiteaOAuthClient:
    def __init__(self, base_url: str, client_id: str, redirect_uri: str, timeout: float = 10.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.client_id = client_id
        self.redirect_uri = redirect_uri
        self.timeout = timeout

    def start(self) -> dict:
        state = secrets.token_urlsafe(32)
        verifier = new_code_verifier()
        challenge = build_pkce_challenge(verifier)
        query = urlencode(
            {
                "client_id": self.client_id,
                "redirect_uri": self.redirect_uri,
                "response_type": "code",
                "code_challenge_method": "S256",
                "code_challenge": challenge,
                "state": state,
                "scope": "read:user read:repository",
            }
        )
        return {
            "status": "redirect",
            "provider": "gitea",
            "authorization_url": f"{self.base_url}/login/oauth/authorize?{query}",
            "state": state,
            "session": {
                "provider": "gitea",
                "base_url": self.base_url,
                "client_id": self.client_id,
                "redirect_uri": self.redirect_uri,
                "code_verifier": verifier,
            },
        }

    def exchange_code(self, code: str, code_verifier: str) -> ProviderToken:
        payload = _post_form(
            f"{self.base_url}/login/oauth/access_token",
            {
                "client_id": self.client_id,
                "redirect_uri": self.redirect_uri,
                "grant_type": "authorization_code",
                "code": code,
                "code_verifier": code_verifier,
            },
            self.timeout,
        )
        return ProviderToken(
            access_token=payload["access_token"],
            token_type=payload.get("token_type", "bearer"),
            scope=payload.get("scope", ""),
        )
```

- [ ] **Step 4: Add authenticated identity helpers**

In `whywiki/collaboration/providers.py`, import `ProviderIdentity` and add these methods:

```python
    def authenticated_identity(self) -> ProviderIdentity:
        from urllib.request import Request, urlopen

        request = Request(
            "https://api.github.com/user",
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {self._token}",
                "User-Agent": "WhyWiki",
            },
            method="GET",
        )
        with urlopen(request, timeout=self._timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return ProviderIdentity(
            provider="github",
            account=payload["login"],
            provider_user_id=str(payload["id"]),
        )
```

Add the Gitea variant inside `GiteaProviderClient`:

```python
    def authenticated_identity(self) -> ProviderIdentity:
        from urllib.request import Request, urlopen

        request = Request(
            f"{self._base_url}/api/v1/user",
            headers={
                "Accept": "application/json",
                "Authorization": f"token {self._token}",
                "User-Agent": "WhyWiki",
            },
            method="GET",
        )
        with urlopen(request, timeout=self._timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return ProviderIdentity(
            provider="gitea",
            base_url=self._base_url,
            account=payload["login"],
            provider_user_id=str(payload["id"]),
        )
```

- [ ] **Step 5: Run OAuth tests and commit**

Run:

```bash
.venv/bin/python -m pytest tests/test_provider_oauth.py tests/test_provider_permissions.py -q
```

Expected: all selected tests pass.

Commit:

```bash
git add whywiki/collaboration/oauth.py whywiki/collaboration/providers.py tests/test_provider_oauth.py tests/test_provider_permissions.py
git commit -m "feat: add git provider oauth clients"
```

---

### Task 3: Token-Backed Provider Registry

**Files:**
- Create: `whywiki/collaboration/registry.py`
- Modify: `whywiki/app.py`
- Test: `tests/test_provider_permissions.py`
- Test: `tests/test_collaboration_api.py`

- [ ] **Step 1: Write failing registry tests**

Append to `tests/test_provider_permissions.py`:

```python
from whywiki.collaboration.models import ProviderIdentity
from whywiki.collaboration.registry import provider_registry_from_accounts
from whywiki.collaboration.tokens import ProviderToken


class _MemoryTokenStore:
    def __init__(self, tokens):
        self.tokens = tokens

    def save(self, identity, token):
        self.tokens[identity.identity_key] = token

    def load(self, identity):
        return self.tokens.get(identity.identity_key)

    def delete(self, identity):
        self.tokens.pop(identity.identity_key, None)


def test_provider_registry_uses_stored_github_token(monkeypatch):
    identity = ProviderIdentity(provider="github", account="alice", provider_user_id="1")
    store = _MemoryTokenStore({"github:1": ProviderToken("github-token")})
    captured = []

    def fake_urlopen(request, timeout):
        captured.append(request)
        return _FakeHTTPResponse({"permissions": {"push": True}})

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    registry = provider_registry_from_accounts([identity], store, env={})

    permission = registry.check_repo(RepoRef(provider="github", repo="owner/repo"))

    assert permission.can_read is True
    assert permission.can_write is True
    assert _request_header(captured[0], "Authorization") == "Bearer github-token"


def test_provider_registry_keeps_static_permissions_for_tests():
    registry = provider_registry_from_accounts(
        [],
        _MemoryTokenStore({}),
        env={"WHYWIKI_COLLAB_STATIC_PERMISSIONS": "github:owner/repo=read"},
    )

    permission = registry.check_repo(RepoRef(provider="github", repo="owner/repo"))

    assert permission.can_read is True
    assert permission.can_write is False
```

Append to `tests/test_collaboration_api.py`:

```python
class _FakeHTTPResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    def __enter__(self) -> "_FakeHTTPResponse":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")


def test_workspace_status_uses_stored_provider_token(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    monkeypatch.setenv("WHYWIKI_DATA_DIR", str(data_dir))
    monkeypatch.setenv("WHYWIKI_ALLOW_FILE_TOKEN_STORE", "1")
    client = TestClient(app)
    client.post("/api/workspace/connect", json={"provider": "github", "repo": "owner/whywiki-memory"})

    from whywiki.collaboration.models import ProviderIdentity
    from whywiki.collaboration.tokens import FileTokenStore, ProviderToken
    account_store = AccountStore(data_dir / "auth" / "accounts.json")
    identity = ProviderIdentity(provider="github", account="alice", provider_user_id="1")
    account_store.save_identity(identity)
    FileTokenStore(data_dir / "auth" / "tokens.json").save(identity, ProviderToken("github-token"))

    def fake_urlopen(request, timeout):
        return _FakeHTTPResponse({"permissions": {"push": True}})

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    response = client.get("/api/workspace/status")

    assert response.status_code == 200
    assert response.json()["access"]["can_enter_workspace"] is True
    assert response.json()["access"]["can_review"] is True
```

Add `import json` and `from whywiki.collaboration.accounts import AccountStore` to the top of `tests/test_collaboration_api.py` when adding this test.

- [ ] **Step 2: Run registry tests and verify they fail**

Run:

```bash
.venv/bin/python -m pytest tests/test_provider_permissions.py tests/test_collaboration_api.py -q
```

Expected: failures for missing `registry.py` and app still using `static_provider_registry_from_env()`.

- [ ] **Step 3: Create `registry.py`**

Create `whywiki/collaboration/registry.py`:

```python
from __future__ import annotations

from collections.abc import Iterable, Mapping

from whywiki.collaboration.env import static_provider_registry_from_env
from whywiki.collaboration.models import ProviderIdentity
from whywiki.collaboration.providers import GiteaProviderClient, GitHubProviderClient, ProviderRegistry
from whywiki.collaboration.tokens import TokenStore


def provider_registry_from_accounts(
    identities: Iterable[ProviderIdentity],
    token_store: TokenStore,
    env: Mapping[str, str] | None = None,
) -> ProviderRegistry:
    registry = static_provider_registry_from_env(env)
    for identity in identities:
        token = token_store.load(identity)
        if token is None:
            continue
        if identity.provider == "github":
            registry.register(identity.provider_key, GitHubProviderClient(token.access_token))
        elif identity.provider == "gitea" and identity.base_url is not None:
            registry.register(identity.provider_key, GiteaProviderClient(identity.base_url, token.access_token))
    return registry
```

- [ ] **Step 4: Wire app workspace status through the token-backed registry**

In `whywiki/app.py`, import `os`, `default_token_store`, `TokenStoreUnavailable`, and `provider_registry_from_accounts`.

Add:

```python
def provider_registry():
    try:
        return provider_registry_from_accounts(account_store().list_identities(), default_token_store(), os.environ)
    except TokenStoreUnavailable:
        return static_provider_registry_from_env()
```

Replace both calls to `static_provider_registry_from_env()` in `collaboration_service_or_none()` and `workspace_status_payload()` with `provider_registry()`.

- [ ] **Step 5: Run registry tests and commit**

Run:

```bash
.venv/bin/python -m pytest tests/test_provider_permissions.py tests/test_collaboration_api.py -q
```

Expected: all selected tests pass.

Commit:

```bash
git add whywiki/collaboration/registry.py whywiki/app.py tests/test_provider_permissions.py tests/test_collaboration_api.py
git commit -m "feat: use stored provider tokens for workspace access"
```

---

### Task 4: Auth API Endpoints

**Files:**
- Modify: `whywiki/app.py`
- Test: `tests/test_auth_api.py`
- Test: `tests/test_collaboration_api.py`

- [ ] **Step 1: Write failing API tests**

Create `tests/test_auth_api.py`:

```python
from fastapi.testclient import TestClient

from whywiki.app import app
from whywiki.collaboration.models import ProviderIdentity
from whywiki.collaboration.tokens import FileTokenStore, ProviderToken


def test_github_device_start_requires_client_id(tmp_path, monkeypatch):
    monkeypatch.setenv("WHYWIKI_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.delenv("WHYWIKI_GITHUB_CLIENT_ID", raising=False)
    client = TestClient(app)

    response = client.post("/api/auth/github/device/start")

    assert response.status_code == 400
    assert "WHYWIKI_GITHUB_CLIENT_ID" in response.json()["detail"]


def test_github_device_poll_saves_identity_without_returning_token(tmp_path, monkeypatch):
    monkeypatch.setenv("WHYWIKI_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("WHYWIKI_GITHUB_CLIENT_ID", "client-id")
    monkeypatch.setenv("WHYWIKI_ALLOW_FILE_TOKEN_STORE", "1")
    client = TestClient(app)

    from whywiki.collaboration.oauth import GitHubDeviceFlowClient
    from whywiki.collaboration.providers import GitHubProviderClient

    monkeypatch.setattr(GitHubDeviceFlowClient, "poll", lambda self, code: {"status": "authorized", "provider": "github", "token": ProviderToken("github-token")})
    monkeypatch.setattr(
        GitHubProviderClient,
        "authenticated_identity",
        lambda self: ProviderIdentity(provider="github", account="alice", provider_user_id="1"),
    )

    response = client.post("/api/auth/github/device/poll", json={"device_code": "device-1"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "connected"
    assert payload["identity"]["account"] == "alice"
    assert "token" not in str(payload).lower()
    assert client.get("/api/auth/accounts").json()["connected_accounts"][0]["account"] == "alice"
    identity = ProviderIdentity(provider="github", account="alice", provider_user_id="1")
    assert FileTokenStore(tmp_path / "data" / "auth" / "tokens.json").load(identity).access_token == "github-token"


def test_gitea_start_requires_base_url_and_client_id(tmp_path, monkeypatch):
    monkeypatch.setenv("WHYWIKI_DATA_DIR", str(tmp_path / "data"))
    client = TestClient(app)

    response = client.post("/api/auth/gitea/start", json={"base_url": "", "client_id": ""})

    assert response.status_code == 400
    assert "base_url" in response.json()["detail"]


def test_delete_account_removes_identity_and_token(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    monkeypatch.setenv("WHYWIKI_DATA_DIR", str(data_dir))
    monkeypatch.setenv("WHYWIKI_ALLOW_FILE_TOKEN_STORE", "1")
    identity = ProviderIdentity(provider="github", account="alice", provider_user_id="1")
    from whywiki.app import account_store
    account_store().save_identity(identity)
    FileTokenStore(data_dir / "auth" / "tokens.json").save(identity, ProviderToken("github-token"))
    client = TestClient(app)

    response = client.delete("/api/auth/accounts/github%3A1")

    assert response.status_code == 200
    assert response.json()["deleted"] is True
    assert account_store().list_identities() == []
    assert FileTokenStore(data_dir / "auth" / "tokens.json").load(identity) is None
```

- [ ] **Step 2: Run API tests and verify they fail**

Run:

```bash
.venv/bin/python -m pytest tests/test_auth_api.py -q
```

Expected: failures for missing auth routes and request models.

- [ ] **Step 3: Add auth request models and route helpers**

In `whywiki/app.py`, add:

```python
import os
from urllib.parse import unquote
```

Add imports:

```python
from .collaboration.oauth import AuthSessionStore, GiteaOAuthClient, GitHubDeviceFlowClient
from .collaboration.providers import GiteaProviderClient, GitHubProviderClient
from .collaboration.tokens import TokenStoreUnavailable, default_token_store
```

Add request models:

```python
class GitHubDevicePollRequest(BaseModel):
    device_code: str


class GiteaStartRequest(BaseModel):
    base_url: str
    client_id: str
```

Add a module-level store:

```python
auth_sessions = AuthSessionStore()
```

Add helpers:

```python
def require_token_store():
    try:
        return default_token_store()
    except TokenStoreUnavailable as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def github_client_id() -> str:
    value = os.getenv("WHYWIKI_GITHUB_CLIENT_ID", "").strip()
    if not value:
        raise HTTPException(status_code=400, detail="Missing WHYWIKI_GITHUB_CLIENT_ID for GitHub login.")
    return value
```

- [ ] **Step 4: Add auth endpoints**

In `whywiki/app.py`, after `/api/auth/accounts`, add:

```python
@app.delete("/api/auth/accounts/{identity_key:path}")
def api_delete_auth_account(identity_key: str) -> dict:
    decoded_key = unquote(identity_key)
    identities = account_store().list_identities()
    identity = next((row for row in identities if row.identity_key == decoded_key), None)
    deleted = account_store().delete_identity(decoded_key)
    if identity is not None:
        require_token_store().delete(identity)
    return {"deleted": deleted}


@app.post("/api/auth/github/device/start")
def api_github_device_start() -> dict:
    return GitHubDeviceFlowClient(github_client_id()).start()


@app.post("/api/auth/github/device/poll")
def api_github_device_poll(req: GitHubDevicePollRequest) -> dict:
    result = GitHubDeviceFlowClient(github_client_id()).poll(req.device_code)
    if result.get("status") != "authorized":
        return result
    token = result["token"]
    identity = GitHubProviderClient(token.access_token).authenticated_identity()
    require_token_store().save(identity, token)
    account_store().save_identity(identity)
    return {"status": "connected", "provider": "github", "identity": identity.to_dict()}


@app.post("/api/auth/gitea/start")
def api_gitea_start(req: GiteaStartRequest) -> dict:
    if not req.base_url.strip():
        raise HTTPException(status_code=400, detail="Gitea base_url is required.")
    if not req.client_id.strip():
        raise HTTPException(status_code=400, detail="Gitea client_id is required.")
    redirect_uri = "http://127.0.0.1:8765/api/auth/gitea/callback"
    result = GiteaOAuthClient(req.base_url, req.client_id, redirect_uri).start()
    auth_sessions.save(result["state"], result["session"])
    return {
        "status": "redirect",
        "provider": "gitea",
        "authorization_url": result["authorization_url"],
        "state": result["state"],
    }


@app.get("/api/auth/gitea/callback", response_class=HTMLResponse)
def api_gitea_callback(code: str | None = None, state: str | None = None, error: str | None = None) -> str:
    if error:
        return f"<html><body><h1>Gitea authorization failed</h1><p>{error}</p></body></html>"
    if not code or not state:
        raise HTTPException(status_code=400, detail="Gitea callback requires code and state.")
    session = auth_sessions.pop(state)
    if session is None:
        raise HTTPException(status_code=400, detail="Gitea callback state is invalid or expired.")
    client = GiteaOAuthClient(session["base_url"], session["client_id"], session["redirect_uri"])
    token = client.exchange_code(code, session["code_verifier"])
    identity = GiteaProviderClient(session["base_url"], token.access_token).authenticated_identity()
    require_token_store().save(identity, token)
    account_store().save_identity(identity)
    return "<html><body><h1>Gitea connected</h1><p>You can return to WhyWiki.</p></body></html>"
```

- [ ] **Step 5: Run API tests and commit**

Run:

```bash
.venv/bin/python -m pytest tests/test_auth_api.py tests/test_collaboration_api.py -q
```

Expected: all selected tests pass.

Commit:

```bash
git add whywiki/app.py tests/test_auth_api.py tests/test_collaboration_api.py
git commit -m "feat: add git provider auth api"
```

---

### Task 5: Frontend Login Flow

**Files:**
- Modify: `whywiki/static/index.html`
- Modify: `whywiki/static/app.js`
- Modify: `whywiki/static/i18n.js`
- Modify: `whywiki/static/styles.css`
- Test: `tests/test_web_assets.py`

- [ ] **Step 1: Write failing web asset tests**

Modify `tests/test_web_assets.py`.

Replace the existing disabled-login test with:

```python
def test_login_provider_buttons_are_real_actions():
    html = (STATIC / "index.html").read_text(encoding="utf-8")

    assert 'id="loginGithubButton"' in html
    assert 'id="loginGiteaButton"' in html
    assert 'id="authConnectionPanel"' in html
    github_button = re.search(r'<button[^>]*id="loginGithubButton"[^>]*>', html)
    gitea_button = re.search(r'<button[^>]*id="loginGiteaButton"[^>]*>', html)
    assert github_button is not None
    assert gitea_button is not None
    assert "disabled" not in github_button.group(0)
    assert "disabled" not in gitea_button.group(0)
```

Append:

```python
def test_app_js_contains_real_auth_flow_hooks():
    content = (STATIC / "app.js").read_text(encoding="utf-8")

    for expected in (
        "startGithubLogin",
        "/api/auth/github/device/start",
        "/api/auth/github/device/poll",
        "startGiteaLogin",
        "/api/auth/gitea/start",
        "disconnectAccount",
        "renderAuthConnectionPanel",
    ):
        assert expected in content


def test_i18n_contains_real_auth_states():
    content = (STATIC / "i18n.js").read_text(encoding="utf-8")

    for expected in (
        "Connect GitHub account",
        "Connect Gitea account",
        "Waiting for authorization",
        "Token storage unavailable",
        "打开 GitHub 授权",
        "令牌存储不可用",
    ):
        assert expected in content
```

- [ ] **Step 2: Run web asset tests and verify they fail**

Run:

```bash
.venv/bin/python -m pytest tests/test_web_assets.py -q
```

Expected: failures because buttons are disabled and auth hooks do not exist.

- [ ] **Step 3: Update static shell**

In `whywiki/static/index.html`, remove `disabled aria-disabled="true"` from both login buttons and add a target inside the collaboration panel:

```html
<div id="authConnectionPanel" class="auth-panel" aria-live="polite"></div>
```

- [ ] **Step 4: Add auth UI functions**

In `whywiki/static/app.js`, add these functions near the collaboration functions:

```javascript
function authPanel() {
  return document.querySelector("#authConnectionPanel");
}

function renderAuthMessage(kind, title, body = "") {
  const panel = authPanel();
  if (!panel) return;
  panel.className = `auth-panel auth-panel--${kind}`;
  panel.replaceChildren(createElement("strong", "", title));
  if (body) panel.append(createElement("p", "muted", body));
}

async function startGithubLogin() {
  renderAuthMessage("loading", t("auth.waiting"), t("auth.githubOpening"));
  try {
    const started = await api("/api/auth/github/device/start", { method: "POST" });
    const panel = authPanel();
    if (!panel) return;
    panel.className = "auth-panel auth-panel--active";
    const code = createElement("code", "auth-code", started.user_code);
    const open = createActionButton(t("auth.openGithub"), "primary", () => window.open(started.verification_uri, "_blank", "noopener"));
    const status = createElement("p", "muted", t("auth.waiting"));
    panel.replaceChildren(createElement("strong", "", t("auth.githubTitle")), code, open, status);
    pollGithubDevice(started.device_code, Number(started.poll_after_seconds || 5), status);
  } catch (error) {
    renderAuthMessage("error", t("auth.setupNeeded"), error.message);
  }
}

async function pollGithubDevice(deviceCode, intervalSeconds, statusNode) {
  window.setTimeout(async () => {
    try {
      const result = await api("/api/auth/github/device/poll", {
        method: "POST",
        body: JSON.stringify({ device_code: deviceCode }),
      });
      if (result.status === "connected") {
        renderAuthMessage("success", t("auth.connected"), providerAccountLabel(result.identity));
        await loadCollaborationStatus();
        return;
      }
      if (result.status === "failed") {
        renderAuthMessage("error", t("auth.failed"), result.error || t("view.error"));
        return;
      }
      if (statusNode) statusNode.textContent = t("auth.waiting");
      pollGithubDevice(deviceCode, Number(result.poll_after_seconds || intervalSeconds || 5), statusNode);
    } catch (error) {
      renderAuthMessage("error", t("auth.failed"), error.message);
    }
  }, Math.max(1, intervalSeconds) * 1000);
}

function renderGiteaForm() {
  const panel = authPanel();
  if (!panel) return;
  const form = document.createElement("form");
  form.className = "inline-form auth-form";
  const baseUrl = document.createElement("input");
  baseUrl.required = true;
  baseUrl.placeholder = "https://git.example.com";
  const clientId = document.createElement("input");
  clientId.required = true;
  clientId.placeholder = t("auth.clientId");
  const submit = document.createElement("button");
  submit.type = "submit";
  submit.className = "action-primary";
  submit.textContent = t("auth.openGitea");
  appendLabeledControl(form, t("auth.giteaBaseUrl"), baseUrl);
  appendLabeledControl(form, t("auth.clientId"), clientId);
  form.append(submit);
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    submit.disabled = true;
    try {
      const result = await api("/api/auth/gitea/start", {
        method: "POST",
        body: JSON.stringify({ base_url: baseUrl.value.trim(), client_id: clientId.value.trim() }),
      });
      window.open(result.authorization_url, "_blank", "noopener");
      renderAuthMessage("loading", t("auth.waiting"), t("auth.giteaReturn"));
    } catch (error) {
      submit.disabled = false;
      renderAuthMessage("error", t("auth.failed"), error.message);
    }
  });
  panel.className = "auth-panel auth-panel--active";
  panel.replaceChildren(createElement("strong", "", t("auth.giteaTitle")), form);
}

function startGiteaLogin() {
  renderGiteaForm();
}

async function disconnectAccount(identityKey) {
  await api(`/api/auth/accounts/${encodeURIComponent(identityKey)}`, { method: "DELETE" });
  await loadCollaborationStatus();
}

function renderAuthConnectionPanel() {
  const github = document.querySelector("#loginGithubButton");
  const gitea = document.querySelector("#loginGiteaButton");
  if (github) github.addEventListener("click", startGithubLogin);
  if (gitea) gitea.addEventListener("click", startGiteaLogin);
}
```

Call `renderAuthConnectionPanel()` immediately before `translate(initialLanguage());` at the bottom of `whywiki/static/app.js`:

```javascript
renderAuthConnectionPanel();
translate(initialLanguage());
loadCollaborationStatus();
loadView("projects");
```

- [ ] **Step 5: Add i18n strings**

In both dictionaries in `whywiki/static/i18n.js`, add keys:

```javascript
"auth.githubTitle": "GitHub authorization",
"auth.giteaTitle": "Gitea authorization",
"auth.openGithub": "Open GitHub authorization",
"auth.openGitea": "Open Gitea authorization",
"auth.githubOpening": "A verification code will appear here. Open GitHub and enter the code.",
"auth.giteaReturn": "After authorizing in Gitea, return to this WhyWiki tab.",
"auth.waiting": "Waiting for authorization",
"auth.connected": "Connected",
"auth.failed": "Authorization failed",
"auth.setupNeeded": "Setup needed",
"auth.tokenStorageUnavailable": "Token storage unavailable",
"auth.clientId": "OAuth client ID",
"auth.giteaBaseUrl": "Gitea server URL",
```

Use the Chinese equivalents:

```javascript
"auth.githubTitle": "GitHub 授权",
"auth.giteaTitle": "Gitea 授权",
"auth.openGithub": "打开 GitHub 授权",
"auth.openGitea": "打开 Gitea 授权",
"auth.githubOpening": "这里会显示验证码。打开 GitHub 后输入该验证码。",
"auth.giteaReturn": "在 Gitea 完成授权后，回到这个 WhyWiki 标签页。",
"auth.waiting": "等待授权",
"auth.connected": "已连接",
"auth.failed": "授权失败",
"auth.setupNeeded": "需要配置",
"auth.tokenStorageUnavailable": "令牌存储不可用",
"auth.clientId": "OAuth client ID",
"auth.giteaBaseUrl": "Gitea 服务器地址",
```

- [ ] **Step 6: Add auth panel styles**

In `whywiki/static/styles.css`, add:

```css
.auth-panel {
  display: grid;
  gap: 0.5rem;
  margin-top: 0.75rem;
  font-size: 0.85rem;
}

.auth-panel:empty {
  display: none;
}

.auth-panel--active,
.auth-panel--loading,
.auth-panel--success,
.auth-panel--error {
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 0.75rem;
  background: var(--surface);
}

.auth-panel--error {
  border-color: var(--danger);
}

.auth-code {
  display: inline-flex;
  width: fit-content;
  max-width: 100%;
  padding: 0.35rem 0.5rem;
  border-radius: 6px;
  background: var(--surface-strong);
  font-size: 1rem;
  letter-spacing: 0;
}

.auth-form {
  gap: 0.625rem;
}
```

Use existing CSS variable names; if one of `--border`, `--surface`, `--surface-strong`, or `--danger` does not exist, use the closest existing variable already used by `.status-pill.warning` and `.action-primary`.

- [ ] **Step 7: Run web tests and commit**

Run:

```bash
node --check whywiki/static/app.js
.venv/bin/python -m pytest tests/test_web_assets.py -q
```

Expected: JavaScript syntax check passes and web asset tests pass.

Commit:

```bash
git add whywiki/static/index.html whywiki/static/app.js whywiki/static/i18n.js whywiki/static/styles.css tests/test_web_assets.py
git commit -m "feat: add git provider login UI"
```

---

### Task 6: Documentation, Feature Status, And Full Verification

**Files:**
- Modify: `README.md`
- Modify: `docs/FEATURE_STATUS.md`
- Modify: `docs/superpowers/specs/2026-05-13-real-git-provider-login-design.md` if implementation reveals a narrow correction

- [ ] **Step 1: Update README collaboration setup**

In `README.md`, under `## Collaboration Model`, add:

```markdown
### Real Provider Login

WhyWiki can connect GitHub and Gitea accounts for local workspace access checks.

- GitHub login uses OAuth device flow. Set `WHYWIKI_GITHUB_CLIENT_ID` before starting WhyWiki.
- Gitea login uses OAuth2 Authorization Code with PKCE. Register a public OAuth application on the Gitea server and use `http://127.0.0.1:8765/api/auth/gitea/callback` as the redirect URL.
- Tokens are stored in the operating system credential store when available: macOS Keychain, Windows Credential Manager / DPAPI-backed storage, or Linux Secret Service.
- `accounts.json` stores only account metadata and never stores tokens.
- If no OS credential backend is available, WhyWiki fails clearly. For local development only, set `WHYWIKI_ALLOW_FILE_TOKEN_STORE=1` to use `.whywiki/auth/tokens.json`.
```

- [ ] **Step 2: Update feature ledger**

In `docs/FEATURE_STATUS.md`, add or update a Git provider row:

```markdown
| Git provider login | Implemented | GitHub device flow and Gitea PKCE connect provider accounts locally. Tokens stay out of `accounts.json` and use OS credential storage or explicit file fallback. |
```

Preserve the existing ledger structure and status vocabulary.

- [ ] **Step 3: Run full verification**

Run:

```bash
node --check whywiki/static/app.js
.venv/bin/python -m compileall whywiki
.venv/bin/python -m pytest -q
```

Expected:

- `node --check` exits 0
- `compileall` exits 0
- pytest reports all tests passing

- [ ] **Step 4: Manual local smoke**

Run:

```bash
./start.sh
```

Open:

```text
http://127.0.0.1:8765/
```

Verify:

- `Connect GitHub account` is clickable.
- Missing `WHYWIKI_GITHUB_CLIENT_ID` shows a setup-needed message.
- With `WHYWIKI_ALLOW_FILE_TOKEN_STORE=1`, token fallback warning path is visible when keyring is unavailable.
- `Connect Gitea account` opens a base URL and client id form.
- `/api/auth/accounts` returns identity metadata only.
- `.whywiki/auth/accounts.json` contains no token-like values.
- `.whywiki/workspace/` contains no token-like values.

- [ ] **Step 5: Commit documentation**

Commit:

```bash
git add README.md docs/FEATURE_STATUS.md docs/superpowers/specs/2026-05-13-real-git-provider-login-design.md
git commit -m "docs: document real git provider login"
```

---

## Self-Review Checklist

- Spec coverage:
  - Token exclusion from `accounts.json`: Task 1 and Task 6.
  - Cross-platform token storage: Task 1.
  - GitHub device flow: Task 2 and Task 4.
  - Gitea PKCE flow: Task 2 and Task 4.
  - Token-backed workspace permissions: Task 3.
  - UI auth states and next steps: Task 5.
  - Documentation and feature ledger: Task 6.
- Placeholder scan:
  - Plan defines concrete files, methods, tests, commands, and expected outcomes. The only remaining uses of the word are literal DOM placeholder attributes in frontend code snippets.
- Type consistency:
  - `ProviderToken`, `TokenStore`, `ProviderIdentity.identity_key`, `AuthSessionStore`, `GitHubDeviceFlowClient`, `GiteaOAuthClient`, and `provider_registry_from_accounts` are introduced before later tasks reference them.
- Scope:
  - This plan does not implement GitHub Apps, GitLab, hosted accounts, workspace push/pull sync, or source repository editing.

## Execution Options

Plan implementation should start from a clean worktree because `main` currently contains committed design context and this feature touches backend auth, frontend UI, and docs.

Recommended execution path:

```bash
git worktree add .worktrees/real-git-provider-login -b real-git-provider-login main
cd .worktrees/real-git-provider-login
```

Then execute tasks one at a time with verification and commits after each task.
