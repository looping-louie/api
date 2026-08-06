# Personas

A persona is a reusable set of agent instructions. Built-in personas are
immutable; they can be enabled, disabled, or used as the source of an editable
custom persona.

## Persona calls

| Method | Path | Description |
| ------ | ---- | ----------- |
| `GET` | `/api/v1/personas` | Lists persona metadata without full instructions. |
| `GET` | `/api/v1/personas/{persona_id}` | Returns a persona including its complete instructions. |
| `POST` | `/api/v1/personas` | Creates a custom persona or copies an available source. |
| `PATCH` | `/api/v1/personas/{persona_id}` | Modifies content or workspace enablement. |
| `DELETE` | `/api/v1/personas/{persona_id}` | Deletes a persona when it has no blocking dependencies. |

## Create Persona Request

| Field | Description |
| ----- | ----------- |
| `name` | Required non-empty display name. |
| `description` | Optional description. Defaults to an empty string. |
| `instructions` | Required non-empty complete persona instructions. |
| `skill_ids` | Ordered IDs of skills associated with the persona. |
| `metadata` | Optional JSON object. Defaults to `{}`. |
| `source_persona_id` | Omit when creating a persona from supplied content. |

To copy an available, non-deprecated persona, send `source_persona_id` and an
optional `name`. The source description, instructions, skills, and metadata are
copied. Do not include those copied fields in the request. If `name` is
omitted, it defaults to the source name followed by ` Copy`.

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

To create a copy instead:

```sh
curl -s -X POST http://127.0.0.1:8000/api/v1/personas \
  -H "Content-Type: application/json" \
  -H "X-Workspace-ID: workspace-id" \
  -d '{
    "source_persona_id": "builtin:persona:tech_lead",
    "name": "Platform lead"
  }'
```

Write and get operations return the complete persona, including `id`,
instructions, `skill_ids`, metadata, origin and capabilities, version, and
timestamps. Deleting a custom skill automatically removes its ID from every
associated persona. List items omit instructions, skill IDs, and metadata.
