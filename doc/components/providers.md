# Providers

The runtime is provider-independent. Provider configuration and the curated
model catalog are exposed through the API; runner and execution code should
depend on capabilities rather than vendor-specific logic.

## Current providers

- Anthropic;
- NVIDIA;
- Ollama;
- OpenAI;
- Together.

The curated model catalog currently contains deployments for Anthropic, OpenAI,
and Together. NVIDIA and Ollama are valid configurable providers, but they do
not yet expose selectable curated deployments. Their provider API response
returns a zero model count and an explicit catalog note until model discovery or
supported deployments are added.

## Future providers

Future providers may include Gemini and enterprise models. Adding a provider
should not require provider-specific behavior in the runner.
