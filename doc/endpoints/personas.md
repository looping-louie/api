# Personas

A persona is a reusable set of agent instructions. Built-in personas are
immutable; they can be enabled or disabled.

## Persona calls

| Method | Path | Description |
| ------ | ---- | ----------- |
| `GET` | `/api/v1/personas` | Lists persona metadata without full instructions. |
| `GET` | `/api/v1/personas/{persona_id}` | Returns a persona including its complete instructions. |
| `POST` | `/api/v1/personas` | Creates a custom persona. |
| `PATCH` | `/api/v1/personas/{persona_id}` | Modifies content or workspace enablement. |
| `DELETE` | `/api/v1/personas/{persona_id}` | Deletes a persona when it has no blocking dependencies. |

The list endpoint returns 12 personas per page and accepts `offset`, `search`,
`status` (`enabled` or `disabled`), repeatable `category`, and `sort`
(`alphabetical-asc`, `alphabetical-desc`, `newest`, or `oldest`). The
`category` values use the same twelve company-area taxonomy as Skills.
Repeated categories use OR semantics. `newest` and `oldest` order by the
persona's `created_at` timestamp, with name and ID providing stable
tie-breakers. Status refers to effective workspace enablement, including
workspace overrides of a built-in default.

## Create Persona Request

| Field | Description |
| ----- | ----------- |
| `name` | Required non-empty display name. |
| `description` | Optional description. Defaults to an empty string. |
| `instructions` | Required non-empty complete persona instructions. |
| `skill_ids` | Ordered IDs of skills associated with the persona. |
| `metadata` | Optional JSON object. `category`, when present, must use the shared company-area taxonomy. Defaults to `{}`. |

## Patch Persona Request

Include at least one of `name`, `description`, `instructions`, `skill_ids`,
`metadata`, or `enabled`. Supplying `skill_ids` replaces the complete
association; an empty list removes every skill. Content changes require
`expected_version`; an enabled-only change does not. `enabled` must be `true`
or `false`, not `null`. Built-in content is immutable, but its enabled state
can be patched.

## Create Persona Example

```sh
curl -s -X POST http://127.0.0.1:8000/api/v1/personas \
  -H "Content-Type: application/json" \
  -H "X-Workspace-ID: workspace-id" \
  -d '{
    "name": "API reviewer",
    "description": "Reviews public API compatibility.",
    "instructions": "Inspect every public contract and report breaking changes.",
    "skill_ids": ["builtin:skill:security"],
    "metadata": {
      "team": "platform"
    }
  }'
```

Write and get operations return the complete persona, including `id`,
instructions, `skill_ids`, metadata, origin and capabilities, version, and
timestamps. Deleting a custom skill automatically removes its ID from every
associated persona. List items omit instructions, skill IDs, and metadata but
include their top-level category.
