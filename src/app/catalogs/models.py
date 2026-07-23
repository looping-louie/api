from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import StrEnum

from .providers import ProviderId


class ModelStatus(StrEnum):
    """Lifecycle state controlled by the curated catalog."""

    ACTIVE = "active"
    DEPRECATED = "deprecated"
    PREVIEW = "preview"


class ModelEndpoint(StrEnum):
    """Provider API used to invoke a model deployment."""

    CHAT_COMPLETIONS = "chat_completions"
    MESSAGES = "messages"
    RESPONSES = "responses"


class ModelCapability(StrEnum):
    """Capabilities relevant to Looping Louie workflows."""

    CODING = "coding"
    FUNCTION_CALLING = "function_calling"
    REASONING = "reasoning"
    STRUCTURED_OUTPUT = "structured_output"
    TEXT = "text"
    VISION = "vision"


@dataclass(frozen=True, slots=True)
class ModelPricing:
    """Token prices for one provider deployment."""

    input_per_million_usd: Decimal
    output_per_million_usd: Decimal
    cached_input_per_million_usd: Decimal | None = None
    valid_until: date | None = None
    note: str | None = None


@dataclass(frozen=True, slots=True)
class ModelDeployment:
    """Provider-specific route through which a logical model is invoked."""

    provider_id: ProviderId
    provider_model_id: str
    endpoint: ModelEndpoint
    context_window: int | None = None
    max_output_tokens: int | None = None
    pricing: ModelPricing | None = None
    status: ModelStatus = ModelStatus.ACTIVE
    deprecated_at: date | None = None


@dataclass(frozen=True, slots=True)
class ModelCatalogEntry:
    """Provider-independent model exposed by Looping Louie."""

    id: str
    name: str
    vendor: str
    family: str
    description: str
    capabilities: frozenset[ModelCapability]
    deployments: tuple[ModelDeployment, ...]
    status: ModelStatus = ModelStatus.ACTIVE
    replacement_model_id: str | None = None
    tags: tuple[str, ...] = field(default_factory=tuple)


def _pricing(
    input_price: str,
    output_price: str,
    cached_input_price: str | None = None,
    *,
    valid_until: date | None = None,
    note: str | None = None,
) -> ModelPricing:
    return ModelPricing(
        input_per_million_usd=Decimal(input_price),
        output_per_million_usd=Decimal(output_price),
        cached_input_per_million_usd=(
            Decimal(cached_input_price)
            if cached_input_price is not None
            else None
        ),
        valid_until=valid_until,
        note=note,
    )


TEXT = frozenset({ModelCapability.TEXT})

GENERAL_REASONING = frozenset(
    {
        ModelCapability.TEXT,
        ModelCapability.VISION,
        ModelCapability.REASONING,
        ModelCapability.FUNCTION_CALLING,
        ModelCapability.STRUCTURED_OUTPUT,
        ModelCapability.CODING,
    }
)

MODEL_CATALOG: tuple[ModelCatalogEntry, ...] = (
    ModelCatalogEntry(
        id="gpt-5.6-sol",
        name="GPT-5.6 Sol",
        vendor="OpenAI",
        family="GPT-5.6",
        description="OpenAI flagship for complex reasoning and coding.",
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
    ModelCatalogEntry(
        id="qwen3.7-max",
        name="Qwen3.7 Max",
        vendor="Qwen",
        family="Qwen3.7",
        description="High-capability Qwen model.",
        capabilities=TEXT,
        deployments=(
            ModelDeployment(
                provider_id=ProviderId.TOGETHER,
                provider_model_id="Qwen/Qwen3.7-Max",
                endpoint=ModelEndpoint.CHAT_COMPLETIONS,
                pricing=_pricing("1.25", "3.75"),
            ),
        ),
        tags=("open-model", "general-purpose"),
    ),
    ModelCatalogEntry(
        id="nemotron-3-ultra",
        name="NVIDIA Nemotron 3 Ultra",
        vendor="NVIDIA",
        family="Nemotron",
        description="Large NVIDIA reasoning model with tool support.",
        capabilities=frozenset(
            {
                ModelCapability.TEXT,
                ModelCapability.REASONING,
                ModelCapability.FUNCTION_CALLING,
                ModelCapability.STRUCTURED_OUTPUT,
            }
        ),
        deployments=(
            ModelDeployment(
                provider_id=ProviderId.TOGETHER,
                provider_model_id="nvidia/nemotron-3-ultra-550b-a55b",
                endpoint=ModelEndpoint.CHAT_COMPLETIONS,
                context_window=512_300,
                pricing=_pricing("0.60", "3.60", "0.20"),
            ),
        ),
        tags=("open-model", "reasoning", "large"),
    ),
    ModelCatalogEntry(
        id="qwen3.5-397b-a17b",
        name="Qwen3.5 397B A17B",
        vendor="Qwen",
        family="Qwen3.5",
        description="Large multimodal mixture-of-experts Qwen model.",
        capabilities=frozenset(
            {
                ModelCapability.TEXT,
                ModelCapability.VISION,
                ModelCapability.REASONING,
            }
        ),
        deployments=(
            ModelDeployment(
                provider_id=ProviderId.TOGETHER,
                provider_model_id="Qwen/Qwen3.5-397B-A17B",
                endpoint=ModelEndpoint.CHAT_COMPLETIONS,
                context_window=262_144,
                pricing=_pricing("0.60", "3.60", "0.35"),
                status=ModelStatus.DEPRECATED,
                deprecated_at=date(2026, 6, 29),
            ),
        ),
        status=ModelStatus.DEPRECATED,
        tags=("open-model", "deprecated"),
    ),
    ModelCatalogEntry(
        id="deepseek-v4-pro",
        name="DeepSeek V4 Pro",
        vendor="DeepSeek",
        family="DeepSeek V4",
        description="Long-context reasoning and coding model.",
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
                provider_model_id="deepseek-ai/DeepSeek-V4-Pro",
                endpoint=ModelEndpoint.CHAT_COMPLETIONS,
                context_window=512_000,
                pricing=_pricing("1.74", "3.48", "0.20"),
            ),
        ),
        tags=("open-model", "coding", "reasoning"),
    ),
    ModelCatalogEntry(
        id="qwen3.6-plus",
        name="Qwen3.6 Plus",
        vendor="Qwen",
        family="Qwen3.6",
        description="Long-context hybrid reasoning model.",
        capabilities=frozenset(
            {
                ModelCapability.TEXT,
                ModelCapability.REASONING,
            }
        ),
        deployments=(
            ModelDeployment(
                provider_id=ProviderId.TOGETHER,
                provider_model_id="Qwen/Qwen3.6-Plus",
                endpoint=ModelEndpoint.CHAT_COMPLETIONS,
                context_window=1_000_000,
                pricing=_pricing("0.50", "3.00"),
            ),
        ),
        tags=("open-model", "long-context", "reasoning"),
    ),
    ModelCatalogEntry(
        id="qwen3.7-plus",
        name="Qwen3.7 Plus",
        vendor="Qwen",
        family="Qwen3.7",
        description="Cost-efficient long-context Qwen model.",
        capabilities=TEXT,
        deployments=(
            ModelDeployment(
                provider_id=ProviderId.TOGETHER,
                provider_model_id="Qwen/Qwen3.7-Plus",
                endpoint=ModelEndpoint.CHAT_COMPLETIONS,
                context_window=1_000_000,
                pricing=_pricing("0.32", "1.28"),
            ),
        ),
        tags=("open-model", "long-context", "cost-efficient"),
    ),
    ModelCatalogEntry(
        id="cogito-v2.1-671b",
        name="Cogito v2.1 671B",
        vendor="Deep Cogito",
        family="Cogito",
        description="Large hybrid reasoning model.",
        capabilities=frozenset(
            {
                ModelCapability.TEXT,
                ModelCapability.REASONING,
            }
        ),
        deployments=(
            ModelDeployment(
                provider_id=ProviderId.TOGETHER,
                provider_model_id="deepcogito/cogito-v2-1-671b",
                endpoint=ModelEndpoint.CHAT_COMPLETIONS,
                context_window=163_840,
                pricing=_pricing("1.25", "1.25"),
            ),
        ),
        tags=("open-model", "reasoning", "large"),
    ),
    ModelCatalogEntry(
        id="minimax-m3",
        name="MiniMax M3",
        vendor="MiniMax",
        family="MiniMax M",
        description="General-purpose multimodal model with tool support.",
        capabilities=frozenset(
            {
                ModelCapability.TEXT,
                ModelCapability.VISION,
                ModelCapability.FUNCTION_CALLING,
                ModelCapability.STRUCTURED_OUTPUT,
            }
        ),
        deployments=(
            ModelDeployment(
                provider_id=ProviderId.TOGETHER,
                provider_model_id="MiniMaxAI/MiniMax-M3",
                endpoint=ModelEndpoint.CHAT_COMPLETIONS,
                context_window=524_288,
                pricing=_pricing("0.30", "1.20", "0.06"),
            ),
        ),
        tags=("open-model", "vision", "cost-efficient"),
    ),
    ModelCatalogEntry(
        id="minimax-m2.7",
        name="MiniMax M2.7",
        vendor="MiniMax",
        family="MiniMax M",
        description="Cost-efficient reasoning model.",
        capabilities=frozenset(
            {
                ModelCapability.TEXT,
                ModelCapability.REASONING,
                ModelCapability.FUNCTION_CALLING,
                ModelCapability.STRUCTURED_OUTPUT,
            }
        ),
        deployments=(
            ModelDeployment(
                provider_id=ProviderId.TOGETHER,
                provider_model_id="MiniMaxAI/MiniMax-M2.7",
                endpoint=ModelEndpoint.CHAT_COMPLETIONS,
                context_window=202_752,
                pricing=_pricing("0.30", "1.20", "0.06"),
            ),
        ),
        tags=("open-model", "reasoning", "cost-efficient"),
    ),
    ModelCatalogEntry(
        id="llama-3.3-70b",
        name="Llama 3.3 70B",
        vendor="Meta",
        family="Llama 3",
        description="General-purpose Llama instruction model.",
        capabilities=frozenset(
            {
                ModelCapability.TEXT,
                ModelCapability.FUNCTION_CALLING,
                ModelCapability.STRUCTURED_OUTPUT,
            }
        ),
        deployments=(
            ModelDeployment(
                provider_id=ProviderId.TOGETHER,
                provider_model_id="meta-llama/Llama-3.3-70B-Instruct-Turbo",
                endpoint=ModelEndpoint.CHAT_COMPLETIONS,
                context_window=131_072,
                pricing=_pricing("1.04", "1.04"),
            ),
        ),
        tags=("open-model", "general-purpose"),
    ),
    ModelCatalogEntry(
        id="gemma-4-31b",
        name="Gemma 4 31B",
        vendor="Google",
        family="Gemma 4",
        description="Compact multimodal Google model.",
        capabilities=frozenset(
            {
                ModelCapability.TEXT,
                ModelCapability.VISION,
                ModelCapability.FUNCTION_CALLING,
                ModelCapability.STRUCTURED_OUTPUT,
            }
        ),
        deployments=(
            ModelDeployment(
                provider_id=ProviderId.TOGETHER,
                provider_model_id="google/gemma-4-31B-it",
                endpoint=ModelEndpoint.CHAT_COMPLETIONS,
                context_window=262_144,
                pricing=_pricing("0.39", "0.97"),
            ),
        ),
        tags=("open-model", "vision", "small"),
    ),
)


MODEL_CATALOG_BY_ID: dict[str, ModelCatalogEntry] = {
    model.id: model
    for model in MODEL_CATALOG
}
