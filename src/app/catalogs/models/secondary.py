"""Additional hosted open-model catalog entries."""

from datetime import date

from ..providers import ProviderId
from .helpers import TEXT, _pricing
from .types import (
    ModelCapability,
    ModelCatalogEntry,
    ModelDeployment,
    ModelEndpoint,
    ModelStatus,
)


SECONDARY_MODEL_CATALOG: tuple[ModelCatalogEntry, ...] = (
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
                max_output_tokens=4096,
                pricing=_pricing("1.74", "3.48", "0.20"),
            ),
            ModelDeployment(
                provider_id=ProviderId.NVIDIA,
                provider_model_id="deepseek-ai/deepseek-v4-pro",
                endpoint=ModelEndpoint.CHAT_COMPLETIONS,
                max_output_tokens=16_384,
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
            ModelDeployment(
                provider_id=ProviderId.NVIDIA,
                provider_model_id="minimaxai/minimax-m3",
                endpoint=ModelEndpoint.CHAT_COMPLETIONS,
                max_output_tokens=8_192,
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
            ModelDeployment(
                provider_id=ProviderId.NVIDIA,
                provider_model_id="google/gemma-4-31b-it",
                endpoint=ModelEndpoint.CHAT_COMPLETIONS,
                max_output_tokens=16_384,
            ),
        ),
        tags=("open-model", "vision", "small"),
    ),
)
