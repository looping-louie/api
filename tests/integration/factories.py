"""Factories shared by SQLite integration tests."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from src.app.models.providers import ProviderCredential
from src.app.services.shared.instruction_service import (
    InstructionDocument,
    InstructionType,
)


DEFAULT_DATETIME = datetime(
    2026,
    7,
    13,
    10,
    0,
    tzinfo=UTC,
)


def build_instruction(
    *,
    instruction_id: str = "instruction-1",
    workspace_id: str = "workspace-1",
    instruction_type: InstructionType = "persona",
    name: str = "Security Reviewer",
    description: str = "Reviews security concerns.",
    instructions: str = "Review the supplied work for security issues.",
    metadata: Mapping[str, Any] | None = None,
    version: int = 1,
    created_at: datetime = DEFAULT_DATETIME,
    updated_at: datetime = DEFAULT_DATETIME,
) -> InstructionDocument:
    """Build one instruction document."""

    return InstructionDocument(
        id=instruction_id,
        workspace_id=workspace_id,
        instruction_type=instruction_type,
        name=name,
        description=description,
        instructions=instructions,
        metadata=dict(metadata or {}),
        version=version,
        created_at=created_at,
        updated_at=updated_at,
    )


def build_provider_credential(
    *,
    credential_id: str = "credential-1",
    workspace_id: str = "workspace-1",
    provider: str = "openai",
    enabled: bool = True,
    enabled_by: str | None = "user-1",
    enabled_on: datetime | None = DEFAULT_DATETIME,
    key_trimmed: str | None = "sk-te***************",
    key_ciphertext: str | None = "encrypted::sk-test-secret",
    key_version: int = 1,
    base_url: str | None = "https://api.openai.com/v1",
    created_at: datetime = DEFAULT_DATETIME,
    updated_at: datetime = DEFAULT_DATETIME,
) -> ProviderCredential:
    """Build one encrypted provider credential."""

    return ProviderCredential(
        id=credential_id,
        workspace_id=workspace_id,
        provider=provider,
        enabled=enabled,
        enabled_by=enabled_by,
        enabled_on=enabled_on,
        key_trimmed=key_trimmed,
        key_ciphertext=key_ciphertext,
        key_version=key_version,
        base_url=base_url,
        created_at=created_at,
        updated_at=updated_at,
    )
