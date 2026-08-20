# Providers (Legacy)

The `/api/v1/providers` routes are a deprecated compatibility surface for
legacy Persona and loop configurations. Do not use them for new integration or
workspace setup.

Use [Catalog](catalog.md) to discover application-owned provider and model
definitions. Use [Linked Services](linked-services.md) to create and manage
named workspace provider connections, including credentials, base URLs, and
enablement. New Persona model selections reference a Linked Service and a
logical catalog model.

The supported provider types are `anthropic`, `nvidia`, `ollama`, `openai`, and
`together`.

## Provider calls

| Method | Path | Description |
| ------ | ---- | ----------- |
| `GET` | `/api/v1/providers` | Lists provider metadata and workspace configuration state. |
| `GET` | `/api/v1/providers/{provider_id}` | Describes one curated provider. |
| `PATCH` | `/api/v1/providers/{provider_id}` | Updates the legacy provider configuration. |
| `DELETE` | `/api/v1/providers/{provider_id}` | Deletes stored legacy configuration. |

## List providers

`GET /api/v1/providers` returns every curated provider as a JSON array. The
route is deprecated and does not paginate.

```http
GET /api/v1/providers
X-Workspace-ID: workspace-acme
```

Example response (`200 OK`):

```json
[
  {
    "provider": "openai",
    "name": "OpenAI",
    "description": "OpenAI hosted models.",
    "logo_url": "/providers/openai.svg",
    "requires_api_key": true,
    "configured": true,
    "enabled": true,
    "key_trimmed": "sk-...abcd",
    "base_url": "https://api.openai.com/v1",
    "model_count": 1,
    "model_catalog_note": null
  }
]
```

## Describe a provider

`GET /api/v1/providers/{provider_id}` returns the same response shape as a
list item for one curated provider.

```http
GET /api/v1/providers/openai
X-Workspace-ID: workspace-acme
```

The endpoint returns `404 provider_not_found` for an unknown provider ID.

## Update a provider

`PATCH /api/v1/providers/{provider_id}` accepts one or more of `api_key`,
`base_url`, and `enabled`. `api_key` is write-only. Set `api_key` to `null` to
clear it, or `base_url` to `null` to restore the catalog default. `enabled`
must be a boolean when supplied.

```http
PATCH /api/v1/providers/openai
X-Workspace-ID: workspace-acme
Content-Type: application/json
```

```json
{
  "enabled": false
}
```

The endpoint returns the updated provider response (`200 OK`). An empty request
returns `422`.

## Delete a provider configuration

`DELETE /api/v1/providers/{provider_id}` removes stored legacy credentials and
configuration for the selected workspace. It does not delete the static
catalog provider definition.

```http
DELETE /api/v1/providers/openai
X-Workspace-ID: workspace-acme
```

Example response (`200 OK`):

```json
{
  "deleted": true
}
```
