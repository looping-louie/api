"""Factories for provider service tests."""

from datetime import UTC, datetime

from src.app.models.providers import ProviderCredential


def build_provider_credential(
    *,
    credential_id: str = "credential-1",
    workspace_id: str = "workspace-1",
    provider: str = "openai",
    enabled: bool = True,
    key_trimmed: str | None = "sk-te***************",
    key_ciphertext: str | None = "encrypted::sk-test-secret",
    base_url: str | None = "https://api.openai.com/v1",
    created_at: datetime | None = None,
    updated_at: datetime | None = None,
) -> ProviderCredential:
    """Build a stored provider credential."""

    now = datetime(2026, 7, 13, 10, 0, tzinfo=UTC)
    created = created_at or now
    updated = updated_at or created

    return ProviderCredential(
        id=credential_id,
        workspace_id=workspace_id,
        provider=provider,
        enabled=enabled,
        enabled_by="user-1" if enabled else None,
        enabled_on=updated if enabled else None,
        key_trimmed=key_trimmed,
        key_ciphertext=key_ciphertext,
        key_version=1,
        base_url=base_url,
        created_at=created,
        updated_at=updated,
    )
