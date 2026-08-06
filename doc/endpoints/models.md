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

## List Models Example

```sh
curl -s \
  "http://127.0.0.1:8000/api/v1/models?capability=coding&available=true" \
  -H "X-Workspace-ID: workspace-id"
```

List items include summary metadata, capabilities, provider IDs, availability,
starting price, and tags. A describe response additionally includes every
provider deployment, its endpoint and limits, pricing, replacement model, and
workspace-specific availability reason.
