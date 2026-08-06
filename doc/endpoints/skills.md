# Skills

A skill is a reusable review or deliberation instruction. Built-in skills are
immutable; they can be enabled, disabled, or used as the source of an editable
custom skill.

## Skill calls

| Method | Path | Description |
| ------ | ---- | ----------- |
| `GET` | `/api/v1/skills` | Lists skill metadata without full instructions. |
| `GET` | `/api/v1/skills/{skill_id}` | Returns a skill including its complete instructions. |
| `POST` | `/api/v1/skills` | Creates a custom skill or copies an available source. |
| `PATCH` | `/api/v1/skills/{skill_id}` | Modifies content or workspace enablement. |
| `DELETE` | `/api/v1/skills/{skill_id}` | Deletes a skill when it has no blocking dependencies. |

## Create Skill Request

| Field | Description |
| ----- | ----------- |
| `name` | Required non-empty display name. |
| `description` | Optional description. Defaults to an empty string. |
| `instructions` | Required non-empty complete skill instructions. |
| `metadata` | Optional skill metadata. Defaults to `{}`. |
| `source_skill_id` | Omit when creating a skill from supplied content. |

Skill metadata may contain `applies_when`, a non-empty list of strings, and
`default_strictness`. Strictness values are integers from 0 to 100 keyed by
`prototype`, `mvp`, and `production`. Extra metadata fields are allowed.

To copy an available, non-deprecated skill, send `source_skill_id` and an
optional `name`. The source description, instructions, and metadata are copied.
Do not include those copied fields in the request. If `name` is omitted, it
defaults to the source name followed by ` Copy`.

## Patch Skill Request

Include at least one of `name`, `description`, `instructions`, `metadata`, or
`enabled`. Content changes require `expected_version`; an enabled-only change
does not. `enabled` must be `true` or `false`, not `null`. Built-in content is
immutable, but its enabled state can be patched.

## Create Skill Example

```sh
curl -s -X POST http://127.0.0.1:8000/api/v1/skills \
  -H "Content-Type: application/json" \
  -H "X-Workspace-ID: workspace-id" \
  -d '{
    "name": "API compatibility",
    "description": "Detects breaking API changes.",
    "instructions": "Compare routes and schemas with the documented contract.",
    "metadata": {
      "applies_when": ["An HTTP contract changes"],
      "default_strictness": {
        "production": 100
      }
    }
  }'
```

To create a copy instead:

```sh
curl -s -X POST http://127.0.0.1:8000/api/v1/skills \
  -H "Content-Type: application/json" \
  -H "X-Workspace-ID: workspace-id" \
  -d '{
    "source_skill_id": "builtin:skill:api_compatibility",
    "name": "Platform API compatibility"
  }'
```

Write and get operations return the complete skill, including `id`,
instructions, metadata, origin and capabilities, version, and timestamps. List
items omit instructions and metadata.
