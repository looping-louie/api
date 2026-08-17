# Catalog

Catalog routes expose application-owned static definitions. They do not include
workspace configuration, credentials, enablement, or effective availability.

## Catalog calls

| Method | Path | Description |
| ------ | ---- | ----------- |
| `GET` | `/api/v1/catalog/providers` | Lists supported static provider types. |
| `GET` | `/api/v1/catalog/models` | Lists active static logical model definitions. |

## List provider catalog

`GET /api/v1/catalog/providers` returns provider metadata that can be used as
the `type` of a future Linked Service. It does not return workspace credentials
or configuration state.

| Property | JSON type | Description |
| -------- | --------- | ----------- |
| `id` | String | Immutable provider identifier, such as `openai`. |
| `name` | String | Human-readable provider name. |
| `description` | String | Static provider description. |
| `logo_url` | String | Provider logo location. |
| `requires_api_key` | Boolean | Whether this provider type requires an API key. |
| `default_base_url` | String or `null` | Default endpoint for this provider type. |
| `model_catalog_note` | String or `null` | Static note about catalog support. |

## List model catalog

`GET /api/v1/catalog/models` returns active logical models. `provider_ids`
describes catalog deployments only; it does not identify configured providers
or available workspace connections.

| Property | JSON type | Description |
| -------- | --------- | ----------- |
| `id` | String | Immutable logical model identifier. |
| `name` | String | Human-readable model name. |
| `vendor` | String | Model vendor. |
| `family` | String | Model family. |
| `description` | String | Static model description. |
| `released_at` | String | ISO 8601 model release date. |
| `capabilities` | Array of strings | Catalog capability identifiers. |
| `status` | String | Static lifecycle status. |
| `provider_ids` | Array of strings | Provider types with an active catalog deployment. |
| `deployment_count` | Integer | Number of catalog deployments for this logical model. |
| `starting_price` | Object or `null` | Lowest active deployment price, when catalog pricing exists. |
| `tags` | Array of strings | Search and grouping tags. |
