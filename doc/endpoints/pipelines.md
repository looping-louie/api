# Pipelines

A pipeline stores an ordered sequence of activity references.
The API manages and validates the definition but does not execute it.

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
by `X-Workspace-ID`. Create the referenced Activities first, then provide their
IDs in execution order. Every referenced Activity must be active and belong to
the same workspace. Repeating an Activity ID is allowed.

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
      "activity_id": "activity-release-review"
    },
    {
      "activity_id": "activity-readiness-quiz"
    },
    {
      "activity_id": "activity-production-approval"
    }
  ]
}
```

The list accepts a non-negative `offset`, optional case-insensitive `search`
over title and description, and optional `status` of `active`, `disabled`, or
`archived`. Active pipelines sort before disabled and archived pipelines.

## Pipeline steps

A step contains only an active activity reference:

```json
{
  "activity_id": "activity-id"
}
```

Every referenced activity must exist in the selected workspace and be active.
Repeated activity references are allowed.

Every create, patch, enablement change, and archival appends a changelog entry
in the same transaction. Step diffs report additions, removals, positional
changes, and order changes.

Request schema failures use the standard API error envelope. Invalid step
structures use `invalid_pipeline_steps`.
