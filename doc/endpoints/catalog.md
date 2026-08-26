# Catalog

Catalog routes expose application-owned static definitions. They do not include
workspace configuration, credentials, enablement, or effective availability.

## Catalog calls

| Method | Path | Description |
| ------ | ---- | ----------- |
| `GET` | `/api/v1/catalog/providers` | Lists supported static provider types. |
| `GET` | `/api/v1/catalog/models` | Lists active static logical model definitions. |
| `GET` | `/api/v1/catalog/personas` | Lists packaged built-in Persona definitions. |
| `GET` | `/api/v1/catalog/skills` | Lists packaged built-in Skill definitions. |

## List provider catalog

`GET /api/v1/catalog/providers` returns provider metadata that can be used as
the `type` of a future Linked Service. It does not return workspace credentials
or configuration state.

```http
GET /api/v1/catalog/providers
```

| Property | JSON type | Description |
| -------- | --------- | ----------- |
| `id` | String | Immutable provider identifier, such as `openai`. |
| `name` | String | Human-readable provider name. |
| `description` | String | Static provider description. |
| `logo_url` | String | Provider logo location. |
| `requires_api_key` | Boolean | Whether this provider type requires an API key. |
| `default_base_url` | String or `null` | Default endpoint for this provider type. |
| `model_catalog_note` | String or `null` | Static note about catalog support. |

Example response (`200 OK`):

```json
[
  {
    "id": "openai",
    "name": "OpenAI",
    "description": "OpenAI hosted models.",
    "logo_url": "/providers/openai.svg",
    "requires_api_key": true,
    "default_base_url": "https://api.openai.com/v1",
    "model_catalog_note": null
  }
]
```

## List model catalog

`GET /api/v1/catalog/models` returns active logical models. Provider-owned
catalog offerings are derived into `provider_ids` and deployment summaries; they
do not identify configured providers or available workspace connections.

```http
GET /api/v1/catalog/models
```

The response is an object with the following properties:

| Property | JSON type | Description |
| -------- | --------- | ----------- |
| `items` | Array | Active logical model definitions. |
| `total` | Integer | Total number of active logical model definitions. |

Each `items` entry has the following properties:

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

Example response (`200 OK`):

```json
{
  "items": [
    {
      "id": "gpt-5",
      "name": "GPT-5",
      "vendor": "OpenAI",
      "family": "GPT",
      "description": "A general-purpose model.",
      "released_at": "2026-08-07",
      "capabilities": ["coding", "text"],
      "status": "active",
      "provider_ids": ["openai"],
      "deployment_count": 1,
      "starting_price": null,
      "tags": ["general-purpose"]
    }
  ],
  "total": 1
}
```

## List built-in Persona catalog

`GET /api/v1/catalog/personas` returns packaged built-in Persona definitions.
It does not return custom Personas, workspace enablement, or workspace action
capabilities.

```http
GET /api/v1/catalog/personas
```

Each array item includes its immutable `id`, `name`, `description`, complete
`instructions`, applicability `metadata`, `enabled_by_default`,
`catalog_version`, `deprecated` state, `category`, associated `skill_ids`, and
the `default_for` agent roles.

Example response (`200 OK`):

```json
[
  {
    "id": "builtin:persona:tech_lead",
    "name": "Tech Lead",
    "description": "Optimises for correct implementation and maintainable code.",
    "instructions": "# Persona: Tech Lead\n...",
    "metadata": {
      "applies_when": ["code", "implementation"],
      "applies_to": ["generator", "reviewer"]
    },
    "enabled_by_default": true,
    "catalog_version": 2,
    "deprecated": false,
    "category": "software_engineering",
    "skill_ids": ["builtin:skill:security"],
    "default_for": ["generator"]
  }
]
```

## List built-in Skill catalog

`GET /api/v1/catalog/skills` returns packaged built-in Skill definitions. It
does not return custom Skills, workspace enablement, or workspace action
capabilities.

```http
GET /api/v1/catalog/skills
```

Each array item includes the shared static instruction fields described for
Personas, plus `reviewer_default_strictness`, `phase`, `artifacts`, and
`output` when the Skill defines them.

Example response (`200 OK`):

```json
[
  {
    "id": "builtin:skill:security",
    "name": "Security",
    "description": "Evaluates security risks.",
    "instructions": "# Security\n...",
    "metadata": {
      "applies_when": ["code", "implementation"],
      "applies_to": ["reviewer"]
    },
    "enabled_by_default": true,
    "catalog_version": 2,
    "deprecated": false,
    "category": "security_privacy",
    "reviewer_default_strictness": {
      "prototype": 40,
      "mvp": 65,
      "production": 85
    },
    "phase": "code_review",
    "artifacts": ["changed_files", "git_diff"],
    "output": "json"
  }
]
```
