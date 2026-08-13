# Models

Model routes expose the curated, provider-independent model catalog and compute
availability from the providers configured in the selected workspace.

## Model calls

| Method | Path | Description |
| ------ | ---- | ----------- |
| `GET` | `/api/v1/models` | Lists models, catalog metadata, pricing, and availability. |
| `GET` | `/api/v1/models/{model_id}` | Returns deployments, capabilities, and availability details. |

## List Models Query

| Parameter | Description |
| --------- | ----------- |
| `provider_id` | Filters by `anthropic`, `nvidia`, `ollama`, `openai`, or `together`. |
| `capability` | Filters by `coding`, `function_calling`, `reasoning`, `structured_output`, `text`, or `vision`. |
| `status` | Filters by catalog status: `active`, `deprecated`, or `preview`. |
| `available` | Filters by effective workspace availability (`true` or `false`). |
| `search` | Searches name, vendor, family, and tags; 1-200 characters. |
| `include_deprecated` | Includes deprecated entries. Defaults to `false`. |

## List models

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
      "providers": ["together"],
      "available": true,
      "starting_price": {
        "input_per_million_usd": "0.6",
        "output_per_million_usd": "2.5",
        "cached_input_per_million_usd": null,
        "valid_until": null,
        "note": null
      },
      "tags": ["coding", "reasoning"]
    }
  ],
  "total": 1
}
```

List items include summary metadata, capabilities, provider IDs, availability,
starting price, and tags. A describe response additionally includes every
provider deployment, its endpoint and limits, pricing, replacement model, and
workspace-specific availability reason.
