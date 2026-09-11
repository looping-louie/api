"""Provider-owned static model offering declarations."""

from datetime import date

from src.app.catalogs.models.items.helpers import _pricing
from src.app.catalogs.models.types import (
    ModelEndpoint,
    ModelStatus,
    ProviderModelOffering,
)
from src.app.catalogs.providers.items import ProviderId

OPENAI_OFFERINGS: tuple[ProviderModelOffering, ...] = (
    ProviderModelOffering(model_id='gpt-5.6-sol', provider_model_id='gpt-5.6-sol', endpoint=ModelEndpoint.RESPONSES, context_window=1050000, max_output_tokens=128000, pricing=_pricing('5.00', '30.00', '0.50'))
    ,
    ProviderModelOffering(model_id='gpt-5.6-terra', provider_model_id='gpt-5.6-terra', endpoint=ModelEndpoint.RESPONSES, context_window=1050000, max_output_tokens=128000, pricing=_pricing('2.50', '15.00', '0.25'))
    ,
    ProviderModelOffering(model_id='gpt-5.6-luna', provider_model_id='gpt-5.6-luna', endpoint=ModelEndpoint.RESPONSES, context_window=1050000, max_output_tokens=128000, pricing=_pricing('1.00', '6.00', '0.10'))
    ,
)

ANTHROPIC_OFFERINGS: tuple[ProviderModelOffering, ...] = (
    ProviderModelOffering(model_id='claude-fable-5', provider_model_id='claude-fable-5', endpoint=ModelEndpoint.MESSAGES, context_window=1000000, max_output_tokens=128000, pricing=_pricing('10.00', '50.00'))
    ,
    ProviderModelOffering(model_id='claude-opus-4.8', provider_model_id='claude-opus-4-8', endpoint=ModelEndpoint.MESSAGES, context_window=1000000, max_output_tokens=128000, pricing=_pricing('5.00', '25.00'))
    ,
    ProviderModelOffering(model_id='claude-sonnet-5', provider_model_id='claude-sonnet-5', endpoint=ModelEndpoint.MESSAGES, context_window=1000000, max_output_tokens=128000, pricing=_pricing('2.00', '10.00', valid_until=date(2026, 8, 31), note='Introductory pricing.'))
    ,
    ProviderModelOffering(model_id='claude-haiku-4.5', provider_model_id='claude-haiku-4-5-20251001', endpoint=ModelEndpoint.MESSAGES, context_window=200000, max_output_tokens=64000, pricing=_pricing('1.00', '5.00'))
    ,
)

TOGETHER_OFFERINGS: tuple[ProviderModelOffering, ...] = (
    ProviderModelOffering(model_id='qwen3.7-max', provider_model_id='Qwen/Qwen3.7-Max', endpoint=ModelEndpoint.CHAT_COMPLETIONS, pricing=_pricing('1.25', '3.75'))
    ,
    ProviderModelOffering(model_id='nemotron-3-ultra', provider_model_id='nvidia/nemotron-3-ultra-550b-a55b', endpoint=ModelEndpoint.CHAT_COMPLETIONS, context_window=512300, pricing=_pricing('0.60', '3.60', '0.20'))
    ,
    ProviderModelOffering(model_id='qwen3.5-397b-a17b', provider_model_id='Qwen/Qwen3.5-397B-A17B', endpoint=ModelEndpoint.CHAT_COMPLETIONS, context_window=262144, pricing=_pricing('0.60', '3.60', '0.35'), status=ModelStatus.DEPRECATED, deprecated_at=date(2026, 6, 29))
    ,
    ProviderModelOffering(model_id='deepseek-v4-pro', provider_model_id='deepseek-ai/DeepSeek-V4-Pro', endpoint=ModelEndpoint.CHAT_COMPLETIONS, context_window=512000, max_output_tokens=4096, pricing=_pricing('1.74', '3.48', '0.20'))
    ,
    ProviderModelOffering(model_id='qwen3.6-plus', provider_model_id='Qwen/Qwen3.6-Plus', endpoint=ModelEndpoint.CHAT_COMPLETIONS, context_window=1000000, pricing=_pricing('0.50', '3.00'))
    ,
    ProviderModelOffering(model_id='qwen3.7-plus', provider_model_id='Qwen/Qwen3.7-Plus', endpoint=ModelEndpoint.CHAT_COMPLETIONS, context_window=1000000, pricing=_pricing('0.32', '1.28'))
    ,
    ProviderModelOffering(model_id='cogito-v2.1-671b', provider_model_id='deepcogito/cogito-v2-1-671b', endpoint=ModelEndpoint.CHAT_COMPLETIONS, context_window=163840, pricing=_pricing('1.25', '1.25'))
    ,
    ProviderModelOffering(model_id='minimax-m3', provider_model_id='MiniMaxAI/MiniMax-M3', endpoint=ModelEndpoint.CHAT_COMPLETIONS, context_window=524288, pricing=_pricing('0.30', '1.20', '0.06'))
    ,
    ProviderModelOffering(model_id='minimax-m2.7', provider_model_id='MiniMaxAI/MiniMax-M2.7', endpoint=ModelEndpoint.CHAT_COMPLETIONS, context_window=202752, pricing=_pricing('0.30', '1.20', '0.06'))
    ,
    ProviderModelOffering(model_id='llama-3.3-70b', provider_model_id='meta-llama/Llama-3.3-70B-Instruct-Turbo', endpoint=ModelEndpoint.CHAT_COMPLETIONS, context_window=131072, pricing=_pricing('1.04', '1.04'))
    ,
    ProviderModelOffering(model_id='gemma-4-31b', provider_model_id='google/gemma-4-31B-it', endpoint=ModelEndpoint.CHAT_COMPLETIONS, context_window=262144, pricing=_pricing('0.39', '0.97'))
    ,
    ProviderModelOffering(model_id='kimi-k2.6', provider_model_id='moonshotai/Kimi-K2.6', endpoint=ModelEndpoint.CHAT_COMPLETIONS, context_window=262144, pricing=_pricing('1.20', '4.50', '0.20'))
    ,
    ProviderModelOffering(model_id='glm-5.2', provider_model_id='zai-org/GLM-5.2', endpoint=ModelEndpoint.CHAT_COMPLETIONS, context_window=262144, max_output_tokens=128000, pricing=_pricing('1.40', '4.40', '0.26'))
    ,
    ProviderModelOffering(model_id='glm-5.1', provider_model_id='zai-org/GLM-5.1', endpoint=ModelEndpoint.CHAT_COMPLETIONS, context_window=202752, pricing=_pricing('1.40', '4.40', '0.26'), status=ModelStatus.DEPRECATED, deprecated_at=date(2026, 6, 26))
    ,
    ProviderModelOffering(model_id='kimi-k2.7-code', provider_model_id='moonshotai/Kimi-K2.7-Code', endpoint=ModelEndpoint.CHAT_COMPLETIONS, context_window=262144, pricing=_pricing('0.95', '4.00', '0.19'))
    ,
)

NVIDIA_OFFERINGS: tuple[ProviderModelOffering, ...] = (
    ProviderModelOffering(model_id='deepseek-v4-pro', provider_model_id='deepseek-ai/deepseek-v4-pro', endpoint=ModelEndpoint.CHAT_COMPLETIONS, max_output_tokens=16384)
    ,
    ProviderModelOffering(model_id='minimax-m3', provider_model_id='minimaxai/minimax-m3', endpoint=ModelEndpoint.CHAT_COMPLETIONS, max_output_tokens=8192)
    ,
    ProviderModelOffering(model_id='gemma-4-31b', provider_model_id='google/gemma-4-31b-it', endpoint=ModelEndpoint.CHAT_COMPLETIONS, max_output_tokens=16384)
    ,
    ProviderModelOffering(model_id='inkling', provider_model_id='thinkingmachines/inkling', endpoint=ModelEndpoint.CHAT_COMPLETIONS, max_output_tokens=8192)
    ,
    ProviderModelOffering(model_id='mistral-medium-3.5-128b', provider_model_id='mistralai/mistral-medium-3.5-128b', endpoint=ModelEndpoint.CHAT_COMPLETIONS, max_output_tokens=16384)
    ,
    ProviderModelOffering(model_id='deepseek-v4-flash', provider_model_id='deepseek-ai/deepseek-v4-flash', endpoint=ModelEndpoint.CHAT_COMPLETIONS, max_output_tokens=16384)
    ,
)

PROVIDER_OFFERINGS: dict[ProviderId, tuple[ProviderModelOffering, ...]] = {
    ProviderId.OPENAI: OPENAI_OFFERINGS,
    ProviderId.ANTHROPIC: ANTHROPIC_OFFERINGS,
    ProviderId.TOGETHER: TOGETHER_OFFERINGS,
    ProviderId.NVIDIA: NVIDIA_OFFERINGS,
}
