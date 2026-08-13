"""OpenAI, Anthropic, and initial hosted model entries."""

from datetime import date

from ..providers import ProviderId
from .helpers import GENERAL_REASONING, _pricing
from .types import (
    ModelCapability,
    ModelCatalogEntry,
    ModelDeployment,
    ModelEndpoint,
    ModelStatus,
)


PRIMARY_MODEL_CATALOG: tuple[ModelCatalogEntry, ...] = (
    ModelCatalogEntry(
        id="gpt-5.6-sol",
        name="GPT-5.6 Sol",
        vendor="OpenAI",
        family="GPT-5.6",
        description="OpenAI flagship for complex reasoning and coding.",
        released_at=date(2026, 7, 9),
        capabilities=GENERAL_REASONING,
        deployments=(
            ModelDeployment(
                provider_id=ProviderId.OPENAI,
                provider_model_id="gpt-5.6-sol",
                endpoint=ModelEndpoint.RESPONSES,
                context_window=1_050_000,
                max_output_tokens=128_000,
                pricing=_pricing("5.00", "30.00", "0.50"),
            ),
        ),
        tags=("frontier", "coding", "reasoning"),
    ),
    ModelCatalogEntry(
        id="gpt-5.6-terra",
        name="GPT-5.6 Terra",
        vendor="OpenAI",
        family="GPT-5.6",
        description="Balanced OpenAI model for quality, latency and cost.",
        released_at=date(2026, 7, 9),
        capabilities=GENERAL_REASONING,
        deployments=(
            ModelDeployment(
                provider_id=ProviderId.OPENAI,
                provider_model_id="gpt-5.6-terra",
                endpoint=ModelEndpoint.RESPONSES,
                context_window=1_050_000,
                max_output_tokens=128_000,
                pricing=_pricing("2.50", "15.00", "0.25"),
            ),
        ),
        tags=("balanced", "coding", "reasoning"),
    ),
    ModelCatalogEntry(
        id="gpt-5.6-luna",
        name="GPT-5.6 Luna",
        vendor="OpenAI",
        family="GPT-5.6",
        description="Cost-efficient OpenAI model for high-volume workloads.",
        released_at=date(2026, 7, 9),
        capabilities=GENERAL_REASONING,
        deployments=(
            ModelDeployment(
                provider_id=ProviderId.OPENAI,
                provider_model_id="gpt-5.6-luna",
                endpoint=ModelEndpoint.RESPONSES,
                context_window=1_050_000,
                max_output_tokens=128_000,
                pricing=_pricing("1.00", "6.00", "0.10"),
            ),
        ),
        tags=("fast", "cost-efficient", "high-volume"),
    ),
    ModelCatalogEntry(
        id="claude-fable-5",
        name="Claude Fable 5",
        vendor="Anthropic",
        family="Claude 5",
        description="Anthropic model for long-running and demanding agents.",
        released_at=date(2026, 6, 9),
        capabilities=GENERAL_REASONING,
        deployments=(
            ModelDeployment(
                provider_id=ProviderId.ANTHROPIC,
                provider_model_id="claude-fable-5",
                endpoint=ModelEndpoint.MESSAGES,
                context_window=1_000_000,
                max_output_tokens=128_000,
                pricing=_pricing("10.00", "50.00"),
            ),
        ),
        tags=("frontier", "agents", "reasoning"),
    ),
    ModelCatalogEntry(
        id="claude-opus-4.8",
        name="Claude Opus 4.8",
        vendor="Anthropic",
        family="Claude 4",
        description="Anthropic model for agentic coding and enterprise work.",
        released_at=date(2026, 5, 28),
        capabilities=GENERAL_REASONING,
        deployments=(
            ModelDeployment(
                provider_id=ProviderId.ANTHROPIC,
                provider_model_id="claude-opus-4-8",
                endpoint=ModelEndpoint.MESSAGES,
                context_window=1_000_000,
                max_output_tokens=128_000,
                pricing=_pricing("5.00", "25.00"),
            ),
        ),
        tags=("coding", "agents", "enterprise"),
    ),
    ModelCatalogEntry(
        id="claude-sonnet-5",
        name="Claude Sonnet 5",
        vendor="Anthropic",
        family="Claude 5",
        description="Anthropic model balancing speed and intelligence.",
        released_at=date(2026, 6, 30),
        capabilities=GENERAL_REASONING,
        deployments=(
            ModelDeployment(
                provider_id=ProviderId.ANTHROPIC,
                provider_model_id="claude-sonnet-5",
                endpoint=ModelEndpoint.MESSAGES,
                context_window=1_000_000,
                max_output_tokens=128_000,
                pricing=_pricing(
                    "2.00",
                    "10.00",
                    valid_until=date(2026, 8, 31),
                    note="Introductory pricing.",
                ),
            ),
        ),
        tags=("balanced", "coding", "agents"),
    ),
    ModelCatalogEntry(
        id="claude-haiku-4.5",
        name="Claude Haiku 4.5",
        vendor="Anthropic",
        family="Claude 4",
        description="Fast Anthropic model for cost-sensitive workloads.",
        released_at=date(2025, 10, 15),
        capabilities=GENERAL_REASONING,
        deployments=(
            ModelDeployment(
                provider_id=ProviderId.ANTHROPIC,
                provider_model_id="claude-haiku-4-5-20251001",
                endpoint=ModelEndpoint.MESSAGES,
                context_window=200_000,
                max_output_tokens=64_000,
                pricing=_pricing("1.00", "5.00"),
            ),
        ),
        tags=("fast", "cost-efficient", "high-volume"),
    ),
    ModelCatalogEntry(
        id="kimi-k2.6",
        name="Kimi K2.6",
        vendor="Moonshot AI",
        family="Kimi",
        description="Multimodal reasoning model for agents and tool use.",
        released_at=date(2026, 4, 20),
        capabilities=GENERAL_REASONING,
        deployments=(
            ModelDeployment(
                provider_id=ProviderId.TOGETHER,
                provider_model_id="moonshotai/Kimi-K2.6",
                endpoint=ModelEndpoint.CHAT_COMPLETIONS,
                context_window=262_144,
                pricing=_pricing("1.20", "4.50", "0.20"),
            ),
        ),
        tags=("open-model", "vision", "agents"),
    ),
    ModelCatalogEntry(
        id="glm-5.2",
        name="GLM-5.2",
        vendor="Z.ai",
        family="GLM",
        description="Reasoning and coding model for long-horizon agents.",
        released_at=date(2026, 6, 16),
        capabilities=frozenset(
            {
                ModelCapability.TEXT,
                ModelCapability.REASONING,
                ModelCapability.FUNCTION_CALLING,
                ModelCapability.STRUCTURED_OUTPUT,
                ModelCapability.CODING,
            }
        ),
        deployments=(
            ModelDeployment(
                provider_id=ProviderId.TOGETHER,
                provider_model_id="zai-org/GLM-5.2",
                endpoint=ModelEndpoint.CHAT_COMPLETIONS,
                context_window=262_144,
                max_output_tokens=128_000,
                pricing=_pricing("1.40", "4.40", "0.26"),
            ),
        ),
        tags=("open-model", "coding", "agents"),
    ),
    ModelCatalogEntry(
        id="glm-5.1",
        name="GLM-5.1",
        vendor="Z.ai",
        family="GLM",
        description="Previous GLM reasoning and function-calling model.",
        released_at=date(2026, 4, 7),
        capabilities=frozenset(
            {
                ModelCapability.TEXT,
                ModelCapability.REASONING,
                ModelCapability.FUNCTION_CALLING,
                ModelCapability.CODING,
            }
        ),
        deployments=(
            ModelDeployment(
                provider_id=ProviderId.TOGETHER,
                provider_model_id="zai-org/GLM-5.1",
                endpoint=ModelEndpoint.CHAT_COMPLETIONS,
                context_window=202_752,
                pricing=_pricing("1.40", "4.40", "0.26"),
                status=ModelStatus.DEPRECATED,
                deprecated_at=date(2026, 6, 26),
            ),
        ),
        status=ModelStatus.DEPRECATED,
        replacement_model_id="glm-5.2",
        tags=("open-model", "deprecated"),
    ),
    ModelCatalogEntry(
        id="kimi-k2.7-code",
        name="Kimi K2.7 Code",
        vendor="Moonshot AI",
        family="Kimi",
        description="Kimi model specialised in coding agents.",
        released_at=date(2026, 6, 12),
        capabilities=GENERAL_REASONING,
        deployments=(
            ModelDeployment(
                provider_id=ProviderId.TOGETHER,
                provider_model_id="moonshotai/Kimi-K2.7-Code",
                endpoint=ModelEndpoint.CHAT_COMPLETIONS,
                context_window=262_144,
                pricing=_pricing("0.95", "4.00", "0.19"),
            ),
        ),
        tags=("open-model", "coding", "agents"),
    ),
)
