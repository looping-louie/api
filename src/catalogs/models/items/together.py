"""Together-hosted curated model items."""

from datetime import date

from .helpers import GENERAL_REASONING, TEXT
from ..types import (
    ModelCapability,
    ModelCatalogEntry,
    ModelLab,
    ModelStatus,
)


TOGETHER_MODEL_ITEMS: tuple[ModelCatalogEntry, ...] = (
    ModelCatalogEntry(
        id="qwen3.7-max",
        name="Qwen3.7 Max",
        vendor="Qwen",
        lab=ModelLab.QWEN,
        family="Qwen3.7",
        description="High-capability Qwen model.",
        released_at=date(2026, 5, 20),
        capabilities=TEXT,
        tags=("open-model", "general-purpose"),
    ),
    ModelCatalogEntry(
        id="nemotron-3-ultra",
        name="NVIDIA Nemotron 3 Ultra",
        vendor="NVIDIA",
        lab=ModelLab.NVIDIA,
        family="Nemotron",
        description="Large NVIDIA reasoning model with tool support.",
        released_at=date(2026, 6, 4),
        capabilities=frozenset(
            {
                ModelCapability.TEXT,
                ModelCapability.REASONING,
                ModelCapability.FUNCTION_CALLING,
                ModelCapability.STRUCTURED_OUTPUT,
            }
        ),
        tags=("open-model", "reasoning", "large"),
    ),
    ModelCatalogEntry(
        id="qwen3.5-397b-a17b",
        name="Qwen3.5 397B A17B",
        vendor="Qwen",
        lab=ModelLab.QWEN,
        family="Qwen3.5",
        description="Large multimodal mixture-of-experts Qwen model.",
        released_at=date(2026, 2, 16),
        capabilities=frozenset(
            {
                ModelCapability.TEXT,
                ModelCapability.VISION,
                ModelCapability.REASONING,
            }
        ),
        status=ModelStatus.DEPRECATED,
        tags=("open-model", "deprecated"),
    ),
    ModelCatalogEntry(
        id="deepseek-v4-pro",
        name="DeepSeek V4 Pro",
        vendor="DeepSeek",
        lab=ModelLab.DEEPSEEK,
        family="DeepSeek V4",
        description="Long-context reasoning and coding model.",
        released_at=date(2026, 4, 24),
        capabilities=frozenset(
            {
                ModelCapability.TEXT,
                ModelCapability.REASONING,
                ModelCapability.FUNCTION_CALLING,
                ModelCapability.STRUCTURED_OUTPUT,
                ModelCapability.CODING,
            }
        ),
        tags=("open-model", "coding", "reasoning"),
    ),
    ModelCatalogEntry(
        id="qwen3.6-plus",
        name="Qwen3.6 Plus",
        vendor="Qwen",
        lab=ModelLab.QWEN,
        family="Qwen3.6",
        description="Long-context hybrid reasoning model.",
        released_at=date(2026, 4, 2),
        capabilities=frozenset(
            {
                ModelCapability.TEXT,
                ModelCapability.REASONING,
            }
        ),
        tags=("open-model", "long-context", "reasoning"),
    ),
    ModelCatalogEntry(
        id="qwen3.7-plus",
        name="Qwen3.7 Plus",
        vendor="Qwen",
        lab=ModelLab.QWEN,
        family="Qwen3.7",
        description="Cost-efficient long-context Qwen model.",
        released_at=date(2026, 6, 1),
        capabilities=TEXT,
        tags=("open-model", "long-context", "cost-efficient"),
    ),
    ModelCatalogEntry(
        id="cogito-v2.1-671b",
        name="Cogito v2.1 671B",
        vendor="Deep Cogito",
        lab=ModelLab.DEEP_COGITO,
        family="Cogito",
        description="Large hybrid reasoning model.",
        released_at=date(2025, 11, 19),
        capabilities=frozenset(
            {
                ModelCapability.TEXT,
                ModelCapability.REASONING,
            }
        ),
        tags=("open-model", "reasoning", "large"),
    ),
    ModelCatalogEntry(
        id="minimax-m3",
        name="MiniMax M3",
        vendor="MiniMax",
        lab=ModelLab.MINIMAX,
        family="MiniMax M",
        description="General-purpose multimodal model with tool support.",
        released_at=date(2026, 6, 1),
        capabilities=frozenset(
            {
                ModelCapability.TEXT,
                ModelCapability.VISION,
                ModelCapability.FUNCTION_CALLING,
                ModelCapability.STRUCTURED_OUTPUT,
            }
        ),
        tags=("open-model", "vision", "cost-efficient"),
    ),
    ModelCatalogEntry(
        id="minimax-m2.7",
        name="MiniMax M2.7",
        vendor="MiniMax",
        lab=ModelLab.MINIMAX,
        family="MiniMax M",
        description="Cost-efficient reasoning model.",
        released_at=date(2026, 3, 18),
        capabilities=frozenset(
            {
                ModelCapability.TEXT,
                ModelCapability.REASONING,
                ModelCapability.FUNCTION_CALLING,
                ModelCapability.STRUCTURED_OUTPUT,
            }
        ),
        tags=("open-model", "reasoning", "cost-efficient"),
    ),
    ModelCatalogEntry(
        id="llama-3.3-70b",
        name="Llama 3.3 70B",
        vendor="Meta",
        lab=ModelLab.META,
        family="Llama 3",
        description="General-purpose Llama instruction model.",
        released_at=date(2024, 12, 6),
        capabilities=frozenset(
            {
                ModelCapability.TEXT,
                ModelCapability.FUNCTION_CALLING,
                ModelCapability.STRUCTURED_OUTPUT,
            }
        ),
        tags=("open-model", "general-purpose"),
    ),
    ModelCatalogEntry(
        id="gemma-4-31b",
        name="Gemma 4 31B",
        vendor="Google",
        lab=ModelLab.GOOGLE,
        family="Gemma 4",
        description="Compact multimodal Google model.",
        released_at=date(2026, 3, 31),
        capabilities=frozenset(
            {
                ModelCapability.TEXT,
                ModelCapability.VISION,
                ModelCapability.FUNCTION_CALLING,
                ModelCapability.STRUCTURED_OUTPUT,
            }
        ),
        tags=("open-model", "vision", "small"),
    ),
    ModelCatalogEntry(
        id="kimi-k2.6",
        name="Kimi K2.6",
        vendor="Moonshot AI",
        lab=ModelLab.MOONSHOT,
        family="Kimi",
        description="Multimodal reasoning model for agents and tool use.",
        released_at=date(2026, 4, 20),
        capabilities=GENERAL_REASONING,
        tags=("open-model", "vision", "agents"),
    ),
    ModelCatalogEntry(
        id="glm-5.2",
        name="GLM-5.2",
        vendor="Z.ai",
        lab=ModelLab.Z,
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
        tags=("open-model", "coding", "agents"),
    ),
    ModelCatalogEntry(
        id="glm-5.1",
        name="GLM-5.1",
        vendor="Z.ai",
        lab=ModelLab.Z,
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
        status=ModelStatus.DEPRECATED,
        replacement_model_id="glm-5.2",
        tags=("open-model", "deprecated"),
    ),
    ModelCatalogEntry(
        id="kimi-k2.7-code",
        name="Kimi K2.7 Code",
        vendor="Moonshot AI",
        lab=ModelLab.MOONSHOT,
        family="Kimi",
        description="Kimi model specialised in coding agents.",
        released_at=date(2026, 6, 12),
        capabilities=GENERAL_REASONING,
        tags=("open-model", "coding", "agents"),
    ),
)
