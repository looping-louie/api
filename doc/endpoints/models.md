# Models

Model routes expose the curated, provider-independent model catalog. Each
provider-owned offering is joined with availability from enabled, configured
Linked Services in the selected workspace.

## Model calls

| Method | Path | Description |
| ------ | ---- | ----------- |
| `GET` | `/api/v1/models` | Lists models, catalog metadata, pricing, and availability. |
| `GET` | `/api/v1/models/{model_id}` | Describes offerings, capabilities, and availability details. |

## List models

| Parameter | Description |
| --------- | ----------- |
| `provider_id` | Filters by `anthropic`, `nvidia`, `ollama`, `openai`, or `together`. |
| `capability` | Filters by `coding`, `function_calling`, `reasoning`, `structured_output`, `text`, or `vision`. |
| `status` | Filters by catalog status: `active`, `deprecated`, or `preview`. |
| `lab` | Filters by one or more repeated, typed lab slugs. Repeated values use OR semantics. |
| `sort` | Orders by `alphabetical-asc`, `alphabetical-desc`, `newest`, or `oldest`. Date sorts use `released_at`. |
| `offset` | Skips filtered results. The endpoint always returns at most 24 models. |
| `available` | Filters by effective workspace availability (`true` or `false`). |
| `search` | Searches name, vendor, family, and tags; 1-200 characters. |
| `include_deprecated` | Includes deprecated entries when no explicit `status` is supplied. Defaults to `false`. |

Supported labs are `anthropic`, `deep-cogito`, `deepseek`, `google`, `meta`,
`minimax`, `mistral`, `moonshot`, `nvidia`, `openai`, `qwen`,
`thinking-machines`, and `z`.

Without `status`, deprecated models are excluded unless
`include_deprecated=true`. An explicit `status=deprecated` selects deprecated
models directly and does not require `include_deprecated=true`.

`GET /api/v1/models` lists catalog entries and their workspace availability.

```http
GET /api/v1/models?capability=coding&available=true
X-Workspace-ID: workspace-acme
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
provider route and workspace-specific availability state. A describe response
uses the same offering shape with replacement-model metadata.

## Describe a model

`GET /api/v1/models/{model_id}` returns every catalog offering joined with its
workspace availability.

```http
GET /api/v1/models/kimi-k2.6
X-Workspace-ID: workspace-acme
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
