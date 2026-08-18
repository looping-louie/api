# Linked Services

Linked Services are workspace-owned, independently named provider connections.
Several services can use the same curated provider type.

| Method | Path | Description |
| ------ | ---- | ----------- |
| `GET` | `/api/v1/linked-services` | Lists workspace linked services. |
| `POST` | `/api/v1/linked-services` | Creates and tests a linked service. |
| `GET` | `/api/v1/linked-services/{id}` | Gets one linked service. |
| `PATCH` | `/api/v1/linked-services/{id}` | Updates mutable settings. |
| `DELETE` | `/api/v1/linked-services/{id}` | Deletes one linked service. |

`id` is immutable. `name`, `enabled`, and `config` are mutable. `provider_type`
must be one of the curated provider identifiers. `config.api_key` is write-only;
responses return `base_url`, `key_trimmed`, `configured`, and static
`available_models` derived from active logical catalog models. Available models
are never stored in the linked-services table.

```json
{
  "name": "primary_openai",
  "provider_type": "openai",
  "enabled": true,
  "config": {
    "api_key": "provider-api-key",
    "base_url": "https://api.openai.com/v1"
  }
}
```

Creation, a config change, and enabling an existing service validate required
settings and test the candidate provider connection before storage.
