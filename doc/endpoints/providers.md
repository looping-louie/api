# Providers

Provider routes manage encrypted credentials and workspace-specific enablement.
The supported `provider_id` values are `anthropic`, `nvidia`, `ollama`,
`openai`, and `together`.

## Provider calls

| Method | Path | Description |
| ------ | ---- | ----------- |
| `GET` | `/api/v1/providers` | Lists catalog providers and their workspace state. |
| `GET` | `/api/v1/providers/{provider_id}` | Describes provider metadata and configuration state. |
| `PATCH` | `/api/v1/providers/{provider_id}` | Updates credentials, base URL, or enabled state. |
| `DELETE` | `/api/v1/providers/{provider_id}` | Deletes workspace configuration and encrypted credentials. |

## List providers

`GET /api/v1/providers` returns every catalog provider and the selected
workspace configuration state.

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
    "description": "OpenAI model provider.",
    "logo_url": "https://example.invalid/openai.svg",
    "requires_api_key": true,
    "configured": true,
    "enabled": true,
    "key_trimmed": "prov****************",
    "base_url": null,
    "model_count": 3,
    "model_catalog_note": "Availability depends on this workspace configuration."
  }
]
```

## Describe a provider

`GET /api/v1/providers/{provider_id}` returns the selected provider's catalog
metadata and workspace configuration state.

```http
GET /api/v1/providers/openai
X-Workspace-ID: workspace-acme
```

Example response (`200 OK`):

```json
{
  "provider": "openai",
  "name": "OpenAI",
  "description": "OpenAI model provider.",
  "logo_url": "https://example.invalid/openai.svg",
  "requires_api_key": true,
  "configured": true,
  "enabled": true,
  "key_trimmed": "prov****************",
  "base_url": null,
  "model_count": 3,
  "model_catalog_note": "Availability depends on this workspace configuration."
}
```

## Update a provider

`PATCH /api/v1/providers/{provider_id}` updates the selected workspace
configuration.

| Field | Description |
| ----- | ----------- |
| `api_key` | New API key. Null clears the stored key; omitted preserves it. |
| `base_url` | Custom base URL. Null restores the catalog default; omitted preserves. |
| `enabled` | Enables or disables the workspace configuration. |

At least one field must be present. Initial configuration is enabled unless
`enabled` is false. Updated credentials and URLs, and configurations being
enabled, are tested before storage. An enabled provider that requires an API
key cannot retain a cleared key. The API never returns the complete key:
provider responses contain only `key_trimmed`.

```http
PATCH /api/v1/providers/openai
X-Workspace-ID: workspace-acme
Content-Type: application/json
```

```json
{
  "api_key": "provider-api-key"
}
```

Example response (`200 OK`):

```json
{
  "provider": "openai",
  "name": "OpenAI",
  "description": "OpenAI model provider.",
  "logo_url": "https://example.invalid/openai.svg",
  "requires_api_key": true,
  "configured": true,
  "enabled": true,
  "key_trimmed": "prov****************",
  "base_url": null,
  "model_count": 3,
  "model_catalog_note": "Availability depends on this workspace configuration."
}
```

Provider GET and PATCH responses contain metadata plus `configured`, `enabled`,
`key_trimmed`, `base_url`, `model_count`, and `model_catalog_note`.
