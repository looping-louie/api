# Personas

A persona is a reusable set of agent instructions. Built-in personas are
immutable; they can be enabled or disabled.

## Persona calls

| Method | Path | Description |
| ------ | ---- | ----------- |
| `GET` | `/api/v1/personas` | Lists persona metadata without full instructions. |
| `GET` | `/api/v1/personas/{persona_id}` | Describes a persona including its complete instructions. |
| `POST` | `/api/v1/personas` | Creates a custom persona. |
| `PATCH` | `/api/v1/personas/{persona_id}` | Modifies content or workspace enablement. |
| `DELETE` | `/api/v1/personas/{persona_id}` | Deletes a persona when it has no blocking dependencies. |

## List personas

`GET /api/v1/personas` returns summary metadata without instructions, skill
IDs, or metadata. An optional `search` matches eligible persona content.

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
      "name": "API reviewer",
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
  "name": "API reviewer",
  "description": "Reviews public API compatibility.",
  "instructions": "Inspect every public contract and report breaking changes.",
  "skill_ids": ["skill-api-compatibility"],
  "metadata": {"team": "platform"},
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

| Field | Description |
| ----- | ----------- |
| `name` | Required non-empty display name. |
| `description` | Optional description. Defaults to an empty string. |
| `instructions` | Required non-empty complete persona instructions. |
| `skill_ids` | Unique ordered IDs of skills associated with the persona. |
| `metadata` | Optional JSON object. Defaults to `{}`. |

```http
POST /api/v1/personas
X-Workspace-ID: workspace-acme
Content-Type: application/json
```

```json
{
  "name": "API reviewer",
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
  "name": "API reviewer",
  "description": "Reviews public API compatibility.",
  "instructions": "Inspect every public contract and report breaking changes.",
  "skill_ids": ["skill-api-compatibility"],
  "metadata": {"team": "platform"},
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
  "name": "API reviewer",
  "description": "Reviews public API compatibility and migration impact.",
  "instructions": "Inspect every public contract and report breaking changes.",
  "skill_ids": ["skill-api-compatibility"],
  "metadata": {"team": "platform"},
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
associated persona. List items omit instructions, skill IDs, and metadata.
