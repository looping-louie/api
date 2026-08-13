# Pipelines

A pipeline stores an ordered sequence of Activity definitions. The API creates
an independent persisted Activity record for every supplied step, then stores
the generated Activity IDs in execution order. The API manages and validates
the definition but does not execute it.

## Pipeline calls

| Method | Path | Description |
| ------ | ---- | ----------- |
| `GET` | `/api/v1/pipelines` | Lists ten filtered pipelines after an offset. |
| `POST` | `/api/v1/pipelines` | Creates an enabled pipeline. |
| `GET` | `/api/v1/pipelines/{pipeline_id}` | Returns one complete ordered definition. |
| `PATCH` | `/api/v1/pipelines/{pipeline_id}` | Updates mutable fields or enablement. |
| `DELETE` | `/api/v1/pipelines/{pipeline_id}` | Archives the pipeline. |
| `GET` | `/api/v1/pipelines/{pipeline_id}/changelog` | Lists ten newest changelog entries. |

Creation requires a non-empty `title`, a `description`, and at least two steps.
New pipelines are enabled. PATCH accepts `title`, `description`, `enabled`, and
`steps`; supplying `steps` replaces the complete ordered array. Archived
pipelines are immutable and omitted from unfiltered listings.

## List pipelines

`GET /api/v1/pipelines` returns ten pipelines after the optional non-negative
`offset`. `search` matches title and description case-insensitively, and
`status` accepts `active`, `disabled`, or `archived`.

```http
GET /api/v1/pipelines?offset=0&status=active&search=release
X-Workspace-ID: workspace-acme
```

Example response (`200 OK`):

```json
{
  "items": [
    {
      "id": "pipeline-production-release-review",
      "title": "Production release review",
      "description": "Review a release, collect readiness information, and request approval.",
      "enabled": true,
      "steps": [
        {"activity_id": "activity-release-review"},
        {"activity_id": "activity-readiness-quiz"},
        {"activity_id": "activity-production-approval"}
      ],
      "created_at": "2026-08-13T10:00:00Z",
      "updated_at": "2026-08-13T10:00:00Z"
    }
  ],
  "total": 1
}
```

## Create a pipeline

`POST /api/v1/pipelines` creates an enabled pipeline in the workspace supplied
by `X-Workspace-ID`. Supply complete Activity definitions in execution order.
The API validates and persists each Activity in the same transaction, assigns
each one an ID, and stores those IDs as Pipeline steps.

```http
POST /api/v1/pipelines
X-Workspace-ID: workspace-acme
Content-Type: application/json
```

```json
{
  "title": "Production release review",
  "description": "Review a release, collect readiness information, and request approval.",
  "steps": [
    {
      "title": "Review release plan",
      "description": "Reach a shared decision about release readiness.",
      "type": "roundtable_loop",
      "config": {
        "stop_conditions": {
          "max_iterations": 2
        },
        "agents": [],
        "output_contract": {
          "type": "text",
          "description": "Release decision."
        }
      }
    },
    {
      "title": "Deployment readiness quiz",
      "description": "Confirm operational readiness before deployment.",
      "type": "quiz",
      "config": {
        "quiz": {
          "questions": []
        }
      }
    },
    {
      "title": "Approve production release",
      "description": "A release manager approves deployment.",
      "type": "approval",
      "config": {}
    }
  ]
}
```

Example response (`201 Created`):

```json
{
  "id": "pipeline-production-release-review",
  "title": "Production release review",
  "description": "Review a release, collect readiness information, and request approval.",
  "enabled": true,
  "steps": [
    {"activity_id": "activity-release-review"},
    {"activity_id": "activity-readiness-quiz"},
    {"activity_id": "activity-production-approval"}
  ],
  "created_at": "2026-08-13T10:00:00Z",
  "updated_at": "2026-08-13T10:00:00Z"
}
```

## Update a pipeline

`PATCH /api/v1/pipelines/{pipeline_id}` accepts one or more of `title`,
`description`, `enabled`, and `steps`. Supplying `steps` replaces the complete
ordered array and creates new independent Activity records from the supplied
inline definitions.

```http
PATCH /api/v1/pipelines/pipeline-production-release-review
X-Workspace-ID: workspace-acme
Content-Type: application/json
```

```json
{
  "enabled": false
}
```

Example response (`200 OK`):

```json
{
  "id": "pipeline-production-release-review",
  "title": "Production release review",
  "description": "Review a release, collect readiness information, and request approval.",
  "enabled": false,
  "steps": [
    {"activity_id": "activity-release-review"},
    {"activity_id": "activity-readiness-quiz"},
    {"activity_id": "activity-production-approval"}
  ],
  "created_at": "2026-08-13T10:00:00Z",
  "updated_at": "2026-08-13T10:15:00Z"
}
```

The list accepts a non-negative `offset`, optional case-insensitive `search`
over title and description, and optional `status` of `active`, `disabled`, or
`archived`. Active pipelines sort before disabled and archived pipelines.

## Pipeline steps

A response step contains the generated ID of its independently persisted
Activity:

```json
{
  "activity_id": "activity-id"
}
```

Pipeline creation and step replacement both accept the same full Activity
definition shape as `POST /api/v1/activities`. Replacing steps creates new
Activity records; it does not modify or delete Activities from prior steps.

Every create, patch, enablement change, and archival appends a changelog entry
in the same transaction. Step diffs report additions, removals, positional
changes, and order changes.

## List pipeline changelog entries

`GET /api/v1/pipelines/{pipeline_id}/changelog` returns ten newest entries
after the optional non-negative `offset`.

```http
GET /api/v1/pipelines/pipeline-production-release-review/changelog?offset=0
X-Workspace-ID: workspace-acme
```

Example response (`200 OK`):

```json
{
  "items": [
    {
      "id": "pipeline-change-002",
      "pipeline_id": "pipeline-production-release-review",
      "change_type": "disabled",
      "actor_id": "user-123",
      "changed_at": "2026-08-13T10:15:00Z",
      "diff": {"enabled": {"from": true, "to": false}},
      "content": null
    }
  ],
  "total": 2
}
```

Request schema failures use the standard API error envelope. Invalid step
structures use `invalid_pipeline_steps`.
