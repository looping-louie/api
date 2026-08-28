# Skills

A skill is a reusable review or deliberation instruction owned by the
authenticated User. Built-in skills are
immutable; they can be enabled or disabled.

## Skill calls

| Method | Path | Description |
| ------ | ---- | ----------- |
| `GET` | `/api/v1/skills` | Lists skill metadata without full instructions. |
| `POST` | `/api/v1/skills` | Creates a custom skill. |
| `GET` | `/api/v1/skills/{skill_id}` | Describes a skill including its complete instructions. |
| `PATCH` | `/api/v1/skills/{skill_id}` | Modifies content or User enablement. |
| `DELETE` | `/api/v1/skills/{skill_id}` | Deletes a skill when it has no blocking dependencies. |

## List skills

`GET /api/v1/skills` returns summary metadata without instructions or metadata.
An optional `search` matches eligible skill content.

The endpoint returns at most 12 skills per request. Use `offset` to move
through the filtered result. `status` accepts `enabled` or `disabled`;
`category` may be repeated to select multiple business categories; and `sort`
accepts `alphabetical-asc`, `alphabetical-desc`, `newest`, or `oldest`.
Repeated categories use OR semantics. `newest` and `oldest` order by
`created_at`, with name and ID providing stable tie-breakers. Status refers to
effective User enablement, including User overrides of a built-in default.

Skills use a deliberately small business taxonomy. The twelve supported
categories are grouped as follows:

- Engineering: `software_engineering`, `quality_reliability`,
  `security_privacy`, and `data_ai`.
- Marketing: `content_brand`, `growth_acquisition`, and `research_analytics`.
- Product & Design: `product_discovery_strategy`, `product_design_ux`, and
  `delivery_planning`.
- Sales & Customer: `sales` and `customer_success_support`.

The department is derived from the selected category rather than stored as a
second independent classification.

```http
GET /api/v1/skills?search=compatibility
X-User-ID: user-acme
```

Example response (`200 OK`):

```json
{
  "items": [
    {
      "id": "skill-api-compatibility",
      "name": "ApiCompatibility",
      "description": "Detects breaking API changes.",
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

## Describe a skill

`GET /api/v1/skills/{skill_id}` returns the complete skill, including
instructions and metadata.

```http
GET /api/v1/skills/skill-api-compatibility
X-User-ID: user-acme
```

Example response (`200 OK`):

```json
{
  "id": "skill-api-compatibility",
  "name": "ApiCompatibility",
  "description": "Detects breaking API changes.",
  "instructions": "Compare routes and schemas with the documented contract.",
  "metadata": {
    "applies_when": [
      "An HTTP contract changes"
    ],
    "default_strictness": {
      "production": 100
    }
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

## Create a skill

`POST /api/v1/skills` creates a custom skill for the User supplied by
`X-User-ID`. Skill routes do not use `X-Project-ID`.

| Field | Description |
| ----- | ----------- |
| `name` | Required non-empty display name. |
| `description` | Optional description. Defaults to an empty string. |
| `instructions` | Required non-empty complete skill instructions. |
| `metadata` | Optional skill metadata. Defaults to an empty object. |

Skill metadata may contain `category`, `applies_when`, a non-empty list of
strings, and `default_strictness`. Strictness values are integers from 0 to 100
keyed by `prototype`, `mvp`, and `production`. Extra metadata fields are
allowed.

```http
POST /api/v1/skills
X-User-ID: user-acme
Content-Type: application/json
```

```json
{
  "name": "ApiCompatibility",
  "description": "Detects breaking API changes.",
  "instructions": "Compare routes and schemas with the documented contract.",
  "metadata": {
    "applies_when": [
      "An HTTP contract changes"
    ],
    "default_strictness": {
      "production": 100
    }
  }
}
```

Example response (`201 Created`):

```json
{
  "id": "skill-api-compatibility",
  "name": "ApiCompatibility",
  "description": "Detects breaking API changes.",
  "instructions": "Compare routes and schemas with the documented contract.",
  "metadata": {
    "applies_when": [
      "An HTTP contract changes"
    ],
    "default_strictness": {
      "production": 100
    }
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

## Update a skill

Include at least one of `name`, `description`, `instructions`, `metadata`, or
`enabled`. Content changes require `expected_version`; an enabled-only change
does not. `enabled` must be `true` or `false`, not `null`. Built-in content is
immutable, but its enabled state can be patched.

```http
PATCH /api/v1/skills/skill-api-compatibility
X-User-ID: user-acme
Content-Type: application/json
```

```json
{
  "expected_version": 1,
  "metadata": {
    "applies_when": [
      "An HTTP contract changes",
      "A migration changes persisted data"
    ],
    "default_strictness": {
      "production": 100
    }
  }
}
```

Example response (`200 OK`):

```json
{
  "id": "skill-api-compatibility",
  "name": "ApiCompatibility",
  "description": "Detects breaking API changes.",
  "instructions": "Compare routes and schemas with the documented contract.",
  "metadata": {
    "applies_when": [
      "An HTTP contract changes",
      "A migration changes persisted data"
    ],
    "default_strictness": {
      "production": 100
    }
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

Write and describe operations return the complete skill, including `id`,
instructions, metadata, origin and capabilities, version, and timestamps. List
items omit instructions and metadata.

## Delete a skill

`DELETE /api/v1/skills/{skill_id}` removes a custom Skill owned by the
authenticated User when no resource depends on it. Built-in Skill content is immutable
and cannot be deleted.

```http
DELETE /api/v1/skills/skill-api-compatibility
X-User-ID: user-acme
```

Example response (`200 OK`):

```json
{
  "deleted": true
}
```

The endpoint returns `409 resource_in_use` when another resource depends on
the Skill, `409 builtin_instruction_immutable` for built-in Skills, and
`404 instruction_not_found` when the Skill is not visible in the selected
User.
