"""Curated model-provider catalog.

This module is the single source of truth for provider identities and their
static product metadata. Workspace credentials and enablement state remain
outside the catalog.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ProviderId(StrEnum):
    """Providers supported by Looping Louie."""

    ANTHROPIC = "anthropic"
    NVIDIA = "nvidia"
    OLLAMA = "ollama"
    OPENAI = "openai"
    TOGETHER = "together"


@dataclass(frozen=True, slots=True)
class ProviderCatalogEntry:
    """Static metadata for one supported model provider."""

    id: ProviderId
    name: str
    description: str
    logo_url: str
    requires_api_key: bool
    default_base_url: str | None
    model_catalog_note: str | None = None


PROVIDER_CATALOG: tuple[ProviderCatalogEntry, ...] = (
    ProviderCatalogEntry(
        id=ProviderId.ANTHROPIC,
        name="Anthropic",
        description=(
            "Access Claude models for reasoning, coding and "
            "long-context review."
        ),
        logo_url="/images/providers/anthropic.jpeg",
        requires_api_key=True,
        default_base_url="https://api.anthropic.com/v1",
    ),
    ProviderCatalogEntry(
        id=ProviderId.NVIDIA,
        name="NVIDIA",
        description=(
            "Access NVIDIA-hosted open models through the NVIDIA NIM API."
        ),
        logo_url="/images/providers/nvidia.jpeg",
        requires_api_key=True,
        default_base_url="https://integrate.api.nvidia.com/v1",
        model_catalog_note=(
            "No curated NVIDIA model deployments are available yet. "
            "Configuring this provider does not currently enable a "
            "selectable model."
        ),
    ),
    ProviderCatalogEntry(
        id=ProviderId.OLLAMA,
        name="Ollama",
        description=(
            "Connect local or self-hosted open-source models through "
            "an Ollama endpoint."
        ),
        logo_url="/images/providers/ollama.jpeg",
        requires_api_key=False,
        default_base_url="http://localhost:11434",
        model_catalog_note=(
            "No curated Ollama model deployments are available yet. "
            "Local model discovery is not currently part of the catalog."
        ),
    ),
    ProviderCatalogEntry(
        id=ProviderId.OPENAI,
        name="OpenAI",
        description=(
            "Access GPT models for generation, reasoning and "
            "specialised reviews."
        ),
        logo_url="/images/providers/openai.jpeg",
        requires_api_key=True,
        default_base_url="https://api.openai.com/v1",
    ),
    ProviderCatalogEntry(
        id=ProviderId.TOGETHER,
        name="Together",
        description=(
            "Access a broad catalogue of hosted open-source models."
        ),
        logo_url="/images/providers/together.jpeg",
        requires_api_key=True,
        default_base_url="https://api.together.xyz/v1",
    ),
)


PROVIDER_CATALOG_BY_ID: dict[ProviderId, ProviderCatalogEntry] = {
    entry.id: entry
    for entry in PROVIDER_CATALOG
}
