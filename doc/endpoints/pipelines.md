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
        "type": "roundtable_loop",
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
        "type": "quiz",
        "quiz": {
          "questions": []
        }
      }
    },
    {
      "title": "Approve production release",
      "description": "A release manager approves deployment.",
      "type": "approval",
      "config": {
        "type": "approval"
      }
    }
  ]
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

Request schema failures use the standard API error envelope. Invalid step
structures use `invalid_pipeline_steps`.
