from __future__ import annotations

from pathlib import Path

from whywiki.collaboration.jsonio import read_json, write_json
from whywiki.collaboration.models import ProviderIdentity

_CONNECTED_ACCOUNTS_KEY = "connected_accounts"


class AccountStore:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    def list_identities(self) -> list[ProviderIdentity]:
        if not self.path.exists():
            return []

        payload = read_json(self.path)
        if not isinstance(payload, dict):
            raise ValueError("account store must contain a JSON object")

        rows = payload.get(_CONNECTED_ACCOUNTS_KEY, [])
        if not isinstance(rows, list):
            raise ValueError("connected_accounts must be a list")

        identities: list[ProviderIdentity] = []
        for row in rows:
            if not isinstance(row, dict):
                raise ValueError("connected account entries must be JSON objects")
            identities.append(ProviderIdentity.from_dict(row))
        return identities

    def save_identity(self, identity: ProviderIdentity) -> None:
        identities = [
            stored_identity
            for stored_identity in self.list_identities()
            if not _is_same_provider_identity(stored_identity, identity)
        ]
        identities.append(identity)
        identities.sort(
            key=lambda stored_identity: (
                stored_identity.provider,
                stored_identity.base_url or "",
                stored_identity.account,
            )
        )

        write_json(
            self.path,
            {_CONNECTED_ACCOUNTS_KEY: [stored_identity.to_dict() for stored_identity in identities]},
        )

    def has_provider_identity(self, provider_key: str) -> bool:
        return any(identity.provider_key == provider_key for identity in self.list_identities())


def _is_same_provider_identity(left: ProviderIdentity, right: ProviderIdentity) -> bool:
    return (
        left.provider == right.provider
        and left.provider_user_id == right.provider_user_id
        and left.base_url == right.base_url
    )
