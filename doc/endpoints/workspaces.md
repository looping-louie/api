# Workspaces

Users own Workspaces. Creating a Workspace creates an `owner` membership for
the requesting User. The first Workspace owned by a User becomes its default;
later Workspaces require `X-Workspace-ID` when the User needs to select one.

Workspace defaults store optional model-target and Harness overrides for the
selected workspace. They are configuration candidates for the hierarchical
execution-default system. Pipeline, Activity, and loop-agent configuration can
define narrower persisted overrides. PipelineRun creation uses Workspace values
only when no narrower Pipeline, Activity, or agent candidate supplies that
execution dimension, then freezes the effective value in its run snapshots.

## Workspace calls

| Method | Path | Description |
| ------ | ---- | ----------- |
| `GET` | `/api/v1/workspaces` | List Workspaces accessible to the current User. |
| `POST` | `/api/v1/workspaces` | Create a Workspace owned by the current User. |
| `GET` | `/api/v1/workspaces/{workspace_id}` | Describe one accessible Workspace. |
| `PATCH` | `/api/v1/workspaces/{workspace_id}` | Update one accessible Workspace. |
| `GET` | `/api/v1/workspaces/{workspace_id}/defaults` | Describes workspace default overrides. |
| `PUT` | `/api/v1/workspaces/{workspace_id}/defaults` | Replaces all workspace default overrides. |
| `GET` | `/api/v1/workspaces/{workspace_id}/models` | Lists available model offerings for a Workspace. |
| `GET` | `/api/v1/workspaces/{workspace_id}/models/{model_id}` | Describes one model's offerings for a Workspace. |

## List workspaces

`GET /api/v1/workspaces` returns every Workspace accessible to the User
identified by `X-User-ID`. The default Workspace appears first.

```http
GET /api/v1/workspaces
X-User-ID: user-123
```

Example response (`200 OK`):

```json
[
  {
    "id": "workspace-acme",
    "name": "Acme",
    "created_at": "2026-08-26T10:00:00Z",
    "updated_at": "2026-08-26T10:00:00Z"
  }
]
```

## Create workspace

`POST /api/v1/workspaces` creates a Workspace owned by the User identified by
`X-User-ID`. The User must first be registered through `POST /api/v1/users`.

```http
POST /api/v1/workspaces
X-User-ID: user-123
Content-Type: application/json
```

```json
{
  "name": "Acme"
}
```

Example response (`201 Created`):

```json
{
  "id": "workspace-acme",
  "name": "Acme",
  "created_at": "2026-08-26T10:00:00Z",
  "updated_at": "2026-08-26T10:00:00Z"
}
```

## Describe workspace

`GET /api/v1/workspaces/{workspace_id}` returns one Workspace accessible to
the User identified by `X-User-ID`.

```http
GET /api/v1/workspaces/workspace-acme
X-User-ID: user-123
```

Example response (`200 OK`):

```json
{
  "id": "workspace-acme",
  "name": "Acme",
  "created_at": "2026-08-26T10:00:00Z",
  "updated_at": "2026-08-26T10:00:00Z"
}
```

## Update workspace

`PATCH /api/v1/workspaces/{workspace_id}` updates mutable metadata for one
Workspace accessible to the User identified by `X-User-ID`. Currently, `name`
is the only mutable field, and it must be supplied with a non-empty value.

```http
PATCH /api/v1/workspaces/workspace-acme
X-User-ID: user-123
Content-Type: application/json
```

```json
{
  "name": "Acme Platform"
}
```

Example response (`200 OK`):

```json
{
  "id": "workspace-acme",
  "name": "Acme Platform",
  "created_at": "2026-08-26T10:00:00Z",
  "updated_at": "2026-08-26T10:15:00Z"
}
```

`model_target` selects one configured linked service and one logical catalog
model. The linked service must belong to the selected workspace, be enabled and
configured, and support an active deployment for `model_id`. `harness` selects
one supported local execution mechanism. Both fields are nullable; `null`
means inherit rather than choose a workspace override.

## Describe workspace defaults

`GET /api/v1/workspaces/{workspace_id}/defaults` returns the specified
accessible workspace's stored overrides. A workspace with no configured record
returns both values as `null`.

```http
GET /api/v1/workspaces/workspace-acme/defaults
X-User-ID: user-123
```

Example response (`200 OK`):

```json
{
  "model_target": {
    "linked_service_id": "linked-service-openai-primary",
    "model_id": "gpt-5"
  },
  "harness": {
    "kind": "codex_cli",
    "version": "v1",
    "config": {}
  },
  "updated_at": "2026-08-25T10:00:00Z"
}
```

## Replace workspace defaults

`PUT /api/v1/workspaces/{workspace_id}/defaults` replaces the complete
workspace override record. Omitting either field and explicitly setting it to
`null` have the same meaning: inherit that dimension.

```http
PUT /api/v1/workspaces/workspace-acme/defaults
X-User-ID: user-123
Content-Type: application/json
```

```json
{
  "model_target": {
    "linked_service_id": "linked-service-openai-primary",
    "model_id": "gpt-5"
  },
  "harness": {
    "kind": "louie",
    "version": "v1",
    "config": {}
  }
}
```

The response has the same shape as `GET`. The endpoint returns
`422 linked_service_selection_unavailable` when the model target cannot be
served by the selected workspace linked service.

## Workspace models

Workspace model routes expose the curated, provider-independent model catalog.
Each provider-owned offering is joined with availability from enabled,
configured Linked Services in the addressed Workspace. The User identified by
`X-User-ID` must have access to `workspace_id`; model routes ignore
`X-Workspace-ID`.

### List workspace models

| Parameter | Description |
| --------- | ----------- |
| `provider_id` | Filters by `anthropic`, `nvidia`, `ollama`, `openai`, or `together`. |
| `capability` | Filters by `coding`, `function_calling`, `reasoning`, `structured_output`, `text`, or `vision`. |
| `status` | Filters by catalog status: `active`, `deprecated`, or `preview`. |
| `lab` | Filters by one or more repeated, typed lab slugs. Repeated values use OR semantics. |
| `sort` | Orders by `alphabetical-asc`, `alphabetical-desc`, `newest`, or `oldest`. Date sorts use `released_at`. |
| `offset` | Skips filtered results. The endpoint always returns at most 24 models. |
| `available` | Filters by effective Workspace availability (`true` or `false`). |
| `search` | Searches name, vendor, family, and tags; 1-200 characters. |
| `include_deprecated` | Includes deprecated entries when no explicit `status` is supplied. Defaults to `false`. |

Supported labs are `anthropic`, `deep-cogito`, `deepseek`, `google`, `meta`,
`minimax`, `mistral`, `moonshot`, `nvidia`, `openai`, `qwen`,
`thinking-machines`, and `z`.

Without `status`, deprecated models are excluded unless
`include_deprecated=true`. An explicit `status=deprecated` selects deprecated
models directly and does not require `include_deprecated=true`.

```http
GET /api/v1/workspaces/workspace-acme/models?capability=coding&available=true
X-User-ID: user-123
```

Example response (`200 OK`):

```json
{
  "items": [
    {
      "id": "kimi-k2.6",
      "name": "Kimi K2.6",
      "vendor": "Moonshot AI",
      "family": "Kimi K2",
      "description": "A coding-capable reasoning model.",
      "capabilities": ["coding", "reasoning", "text"],
      "status": "active",
      "available": true,
      "offerings": [
        {
          "provider_id": "together",
          "provider_model_id": "moonshotai/Kimi-K2.6",
          "endpoint": "chat_completions",
          "context_window": 262144,
          "max_output_tokens": 32768,
          "pricing": {
            "input_per_million_usd": "0.6",
            "output_per_million_usd": "2.5",
            "cached_input_per_million_usd": null,
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
      "tags": ["coding", "reasoning"]
    }
  ],
  "total": 1
}
```

List items include summary metadata, the model version's `released_at` date,
capabilities, offerings, availability, and tags. Each offering contains its
provider route and Workspace-specific availability state.

### Describe a workspace model

`GET /api/v1/workspaces/{workspace_id}/models/{model_id}` returns every catalog
offering joined with its availability in the addressed Workspace.

```http
GET /api/v1/workspaces/workspace-acme/models/kimi-k2.6
X-User-ID: user-123
```

Example response (`200 OK`):

```json
{
  "id": "kimi-k2.6",
  "name": "Kimi K2.6",
  "vendor": "Moonshot AI",
  "family": "Kimi K2",
  "description": "A coding-capable reasoning model.",
  "capabilities": ["coding", "reasoning", "text"],
  "status": "active",
  "replacement_model_id": null,
  "tags": ["coding", "reasoning"],
  "offerings": [
    {
      "provider_id": "together",
      "provider_model_id": "moonshotai/Kimi-K2.6",
      "endpoint": "chat_completions",
      "context_window": 262144,
      "max_output_tokens": 32768,
      "pricing": {
        "input_per_million_usd": "0.6",
        "output_per_million_usd": "2.5",
        "cached_input_per_million_usd": null,
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
