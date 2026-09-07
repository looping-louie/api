# Users

Users are durable top-level identities. Authentication is not implemented yet;
clients identify the acting user with `X-User-ID`. The User resource has no
profile fields beyond execution settings. `settings.default_model_id` and
`settings.default_harness` are inherited by owned Pipeline and Activity runs
when no narrower override is configured.
`settings.default_model_availability` controls whether unconfigured catalog
models are available; it defaults to `enabled`. `configured_models` overrides
that default for individual logical model IDs.

## Resource endpoints

| Method | Path | Purpose |
| ------ | ---- | ------- |
| `POST` | `/api/v1/users` | Register the current user if it is new. |
| `GET` | `/api/v1/users/me` | Return the registered current user. |
| `PATCH` | `/api/v1/users/me` | Replace current-user execution settings. |
| `GET` | `/api/v1/users/me/models` | List catalog models and current-user availability. |
| `GET` | `/api/v1/users/me/models/{model_id}` | Describe one model and current-user availability. |

## Register the current user

`POST /api/v1/users` persists the identity supplied in `X-User-ID`. Repeated
requests are idempotent and preserve the original timestamps.

```http
POST /api/v1/users
X-User-ID: user-123
```

Example response (`201 Created`):

```json
{
  "id": "user-123",
  "settings": {
    "default_model_id": null,
    "default_harness": null,
    "default_model_availability": "enabled",
    "configured_models": [
    ]
  },
  "created_at": "2026-08-26T10:00:00Z",
  "updated_at": "2026-08-26T10:00:00Z"
}
```

## Get the current user

`GET /api/v1/users/me` returns the user identified by `X-User-ID`. It returns
`404 user_not_found` until that identity has been registered.

```http
GET /api/v1/users/me
X-User-ID: user-123
```

Example response (`200 OK`):

```json
{
  "id": "user-123",
  "settings": {
    "default_model_id": null,
    "default_harness": null,
    "default_model_availability": "enabled",
    "configured_models": [
    ]
  },
  "created_at": "2026-08-26T10:00:00Z",
  "updated_at": "2026-08-26T10:00:00Z"
}
```

## Update user settings

`PATCH /api/v1/users/me` replaces the User's execution settings. A `null`
`default_model_id` or `default_harness` clears the corresponding User-level
override. Configured values are used only after narrower Activity and Pipeline
candidates are absent.
`configured_models` contains unique logical model IDs with an `enabled` or
`disabled` status. An entry overrides `default_model_availability`; a disabled
model remains unavailable even when a compatible Linked Service is ready.

```http
PATCH /api/v1/users/me
X-User-ID: user-123
Content-Type: application/json

{
  "default_model_id": "gpt-5",
  "default_harness": {
    "kind": "codex_cli"
  },
  "default_model_availability": "disabled",
  "configured_models": [
    {
      "id": "gpt-5",
      "status": "enabled"
    }
  ]
}
```

Example response (`200 OK`):

```json
{
  "id": "user-123",
  "settings": {
    "default_model_id": "gpt-5",
    "default_harness": {
      "kind": "codex_cli",
      "version": "v1",
      "config": {
      }
    },
    "default_model_availability": "disabled",
    "configured_models": [
      {
        "id": "gpt-5",
        "status": "enabled"
      }
    ]
  },
  "created_at": "2026-08-26T10:00:00Z",
  "updated_at": "2026-08-26T10:05:00Z"
}
```

## User models

`GET /api/v1/users/me/models` exposes the curated provider-independent model
catalog. Each offering is joined with the current User's configured Linked
Services and model availability policy. `X-Project-ID` is ignored.

`available=true` or `available=false` filters by effective availability. A
model must be enabled by the User's settings and offered by an enabled,
configured Linked Service to be available. The endpoint accepts `provider_id`,
`capability`, `status`, repeated `lab`, `sort`, `offset`, `available`, `search`,
and `include_deprecated` filters.

```http
GET /api/v1/users/me/models?capability=coding&available=true
X-User-ID: user-123
```

Example response (`200 OK`):

```json
{
  "items": [
    {
      "id": "gpt-5",
      "name": "GPT-5",
      "vendor": "OpenAI",
      "family": "GPT-5",
      "description": "A general-purpose model for coding and reasoning.",
      "released_at": "2025-08-07",
      "capabilities": [
        "coding",
        "text",
        "reasoning"
      ],
      "status": "active",
      "enabled": true,
      "available": true,
      "offerings": [
        {
          "provider_id": "openai",
          "provider_model_id": "gpt-5",
          "endpoint": "responses",
          "context_window": 400000,
          "max_output_tokens": 128000,
          "pricing": {
            "input_per_million_usd": "1.25",
            "output_per_million_usd": "10.00",
            "cached_input_per_million_usd": "0.125",
            "valid_until": null,
            "note": null
          },
          "status": "active",
          "deprecated_at": null,
          "configured": true,
          "enabled": true,
          "available": true,
          "reason": null
        }
      ],
      "tags": [
        "coding",
        "reasoning"
      ]
    }
  ],
  "total": 1
}
```

Top-level `enabled` is the independent User policy signal. A `codex_cli`
selector uses it because the worker authenticates the CLI locally; top-level
`available` remains the stronger `louie` signal that also requires a configured
Linked Service.

`GET /api/v1/users/me/models/{model_id}` returns every catalog offering for one
logical model. Both model-list items and this response expose the same top-level
`enabled` and `available` booleans and the same offering-level `configured`,
`enabled`, `available`, and `reason` fields. The single-model response
additionally includes `replacement_model_id`.

```http
GET /api/v1/users/me/models/gpt-5
X-User-ID: user-123
```

Example response (`200 OK`):

```json
{
  "id": "gpt-5",
  "name": "GPT-5",
  "vendor": "OpenAI",
  "family": "GPT-5",
  "description": "A general-purpose model for coding and reasoning.",
  "released_at": "2025-08-07",
  "capabilities": [
    "coding",
    "text",
    "reasoning"
  ],
  "status": "active",
  "enabled": true,
  "replacement_model_id": null,
  "tags": [
    "coding",
    "reasoning"
  ],
  "offerings": [
    {
      "provider_id": "openai",
      "provider_model_id": "gpt-5",
      "endpoint": "responses",
      "context_window": 400000,
      "max_output_tokens": 128000,
      "pricing": {
        "input_per_million_usd": "1.25",
        "output_per_million_usd": "10.00",
        "cached_input_per_million_usd": "0.125",
        "valid_until": null,
        "note": null
      },
      "status": "active",
      "deprecated_at": null,
      "configured": true,
      "enabled": true,
      "available": true,
      "reason": null
    }
  ],
  "available": true
}
```
