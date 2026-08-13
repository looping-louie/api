# Skills

A skill is a reusable review or deliberation instruction. Built-in skills are
immutable; they can be enabled or disabled.

## Skill calls

| Method | Path | Description |
| ------ | ---- | ----------- |
| `GET` | `/api/v1/skills` | Lists skill metadata without full instructions. |
| `GET` | `/api/v1/skills/{skill_id}` | Returns a skill including its complete instructions. |
| `POST` | `/api/v1/skills` | Creates a custom skill. |
| `PATCH` | `/api/v1/skills/{skill_id}` | Modifies content or workspace enablement. |
| `DELETE` | `/api/v1/skills/{skill_id}` | Deletes a skill when it has no blocking dependencies. |

The list endpoint returns at most 12 skills per request. Use `offset` to move
through the filtered result. `status` accepts `enabled` or `disabled`;
`category` may be repeated to select multiple business categories; and `sort`
accepts `alphabetical-asc`, `alphabetical-desc`, `newest`, or `oldest`.

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

## Create Skill Request

| Field | Description |
| ----- | ----------- |
| `name` | Required non-empty display name. |
| `description` | Optional description. Defaults to an empty string. |
| `instructions` | Required non-empty complete skill instructions. |
| `metadata` | Optional skill metadata. Defaults to `{}`. |

Skill metadata may contain `category`, `applies_when`, a non-empty list of
strings, and `default_strictness`. Strictness values are integers from 0 to 100
keyed by `prototype`, `mvp`, and `production`. Extra metadata fields are
allowed.

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

Write and get operations return the complete skill, including `id`,
instructions, metadata, origin and capabilities, version, and timestamps. List
items omit instructions and metadata.
