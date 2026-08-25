# Personas

A persona is a reusable set of agent instructions. Built-in personas are
immutable; they can be enabled or disabled.

## Persona calls

| Method | Path | Description |
| ------ | ---- | ----------- |
| `GET` | `/api/v1/personas` | Lists persona metadata without full instructions. |
| `POST` | `/api/v1/personas` | Creates a custom persona. |
| `GET` | `/api/v1/personas/{persona_id}` | Describes a persona including its complete instructions. |
| `PATCH` | `/api/v1/personas/{persona_id}` | Modifies content or workspace enablement. |
| `DELETE` | `/api/v1/personas/{persona_id}` | Deletes a persona when it has no blocking dependencies. |

## List personas

`GET /api/v1/personas` returns summary metadata without instructions, skill
IDs, or metadata. An optional `search` matches eligible persona content.

The endpoint returns 12 personas per page and accepts `offset`, `search`,
`status` (`enabled` or `disabled`), repeatable `category`, and `sort`
(`alphabetical-asc`, `alphabetical-desc`, `newest`, or `oldest`). Repeated
categories use OR semantics. `newest` and `oldest` order by `created_at`, with
name and ID providing stable tie-breakers. Status refers to effective workspace
enablement, including workspace overrides of a built-in default. List items
include the top-level category.

```http
GET /api/v1/personas?search=api
X-Workspace-ID: workspace-acme
```

Example response (`200 OK`):

```json
{
  "items": [
    {
      "id": "persona-api-reviewer",
      "name": "ApiReviewer",
      "description": "Reviews public API compatibility.",
      "origin": "custom",
      "enabled": true,
      "editable": true,
      "duplicable": true,
      "deprecated": false,
      "catalog_version": null,
      "source_instruction_id": null,
      "version": 1,
      "created_at": "2026-08-13T10:00:00Z",
      "updated_at": "2026-08-13T10:00:00Z"
    }
  ],
  "total": 1
}
```

## Describe a persona

`GET /api/v1/personas/{persona_id}` returns the complete persona, including
instructions, associated skill IDs, and metadata.

```http
GET /api/v1/personas/persona-api-reviewer
X-Workspace-ID: workspace-acme
```

Example response (`200 OK`):

```json
{
  "id": "persona-api-reviewer",
  "name": "ApiReviewer",
  "description": "Reviews public API compatibility.",
  "instructions": "Inspect every public contract and report breaking changes.",
  "skill_ids": [
    "skill-api-compatibility"
    ],
  "metadata": {
    "team": "platform"
  },
  "origin": "custom",
  "enabled": true,
  "editable": true,
  "duplicable": true,
  "deprecated": false,
  "catalog_version": null,
  "source_instruction_id": null,
  "version": 1,
  "created_at": "2026-08-13T10:00:00Z",
  "updated_at": "2026-08-13T10:00:00Z"
}
```

## Create a persona

`POST /api/v1/personas` creates a custom persona in the workspace supplied by
`X-Workspace-ID`.

| Field | JSON type | Create | Update | Restrictions |
| ----- | --------- | ------ | ------ | ------------ |
| `name` | String | Required | Optional | Contains 1 to 140 characters. Starts with a Unicode letter, number, or `_`. Does not contain whitespace, `.`, `+`, `?`, `/`, `<`, `>`, `*`, `%`, `&`, or `:`. |
| `description` | String | Optional | Optional | Defaults to an empty string on create. May be empty. |
| `instructions` | String | Required | Optional | Must not be empty. |
| `skill_ids` | Array of strings | Optional | Optional | Contains unique ordered IDs of available skills. Defaults to `[]` on create. |
| `metadata` | Object | Optional | Optional | `category`, when present, must use the shared company-area taxonomy. Defaults to `{}` on create. |
| `expected_version` | Integer | Not allowed | Required for content changes | Positive current Persona version. Not required for an enablement-only update. |
| `enabled` | Boolean | Not allowed | Optional | Enables or disables the Persona in the selected workspace. |

```http
POST /api/v1/personas
X-Workspace-ID: workspace-acme
Content-Type: application/json
```

```json
{
  "name": "ApiReviewer",
  "description": "Reviews public API compatibility.",
  "instructions": "Inspect every public contract and report breaking changes.",
  "skill_ids": [
    "skill-api-compatibility"
  ],
  "metadata": {
    "team": "platform"
  }
}
```

Example response (`201 Created`):

```json
{
  "id": "persona-api-reviewer",
  "name": "ApiReviewer",
  "description": "Reviews public API compatibility.",
  "instructions": "Inspect every public contract and report breaking changes.",
  "skill_ids": [
    "skill-api-compatibility"
  ],
  "metadata": {
    "team": "platform"
  },
  "origin": "custom",
  "enabled": true,
  "editable": true,
  "duplicable": true,
  "deprecated": false,
  "catalog_version": null,
  "source_instruction_id": null,
  "version": 1,
  "created_at": "2026-08-13T10:00:00Z",
  "updated_at": "2026-08-13T10:00:00Z"
}
```

## Update a persona

Include at least one of `name`, `description`, `instructions`, `skill_ids`,
`metadata`, or `enabled`. Supplying `skill_ids` replaces the complete
association; an empty list removes every skill. Content changes require
`expected_version`; an enabled-only change does not. `enabled` must be `true`
or `false`, not `null`. Built-in content is immutable, but its enabled state
can be patched.

```http
PATCH /api/v1/personas/persona-api-reviewer
X-Workspace-ID: workspace-acme
Content-Type: application/json
```

```json
{
  "expected_version": 1,
  "description": "Reviews public API compatibility and migration impact."
}
```

Example response (`200 OK`):

```json
{
  "id": "persona-api-reviewer",
  "name": "ApiReviewer",
  "description": "Reviews public API compatibility and migration impact.",
  "instructions": "Inspect every public contract and report breaking changes.",
  "skill_ids": [
    "skill-api-compatibility"
  ],
  "metadata": {
    "team": "platform"
  },
  "origin": "custom",
  "enabled": true,
  "editable": true,
  "duplicable": true,
  "deprecated": false,
  "catalog_version": null,
  "source_instruction_id": null,
  "version": 2,
  "created_at": "2026-08-13T10:00:00Z",
  "updated_at": "2026-08-13T10:15:00Z"
}
```

Write and describe operations return the complete persona, including `id`,
instructions, `skill_ids`, metadata, origin and capabilities, version, and
timestamps. Deleting a custom skill automatically removes its ID from every
associated persona. List items omit instructions, skill IDs, and metadata but
include their top-level category.

## Delete a persona

`DELETE /api/v1/personas/{persona_id}` removes a custom Persona from the
selected workspace when no resource depends on it. Built-in Persona content is
immutable and cannot be deleted.

```http
DELETE /api/v1/personas/persona-api-reviewer
X-Workspace-ID: workspace-acme
```

Example response (`200 OK`):

```json
{
  "deleted": true
}
```

The endpoint returns `409 resource_in_use` when another resource depends on
the Persona, `409 builtin_instruction_immutable` for built-in Personas, and
`404 instruction_not_found` when the Persona is not visible in the selected
workspace.
