# Providers (Legacy)

The `/api/v1/providers` routes are retained only as a deprecated compatibility
surface for legacy Persona and loop configurations. Do not use them for new
integration or workspace setup.

Use [Catalog](catalog.md) to discover application-owned provider and model
definitions. Use [Linked Services](linked-services.md) to create and manage
named workspace provider connections, including credentials, base URLs, and
enablement. New Persona model selections reference a Linked Service and a
logical catalog model.

The supported provider types are `anthropic`, `nvidia`, `ollama`, `openai`, and
`together`.
