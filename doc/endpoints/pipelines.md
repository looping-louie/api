# Pipelines

A pipeline stores a declared sequence of Activity definitions. The API creates
an independent persisted Activity record for every supplied step, then stores
the generated Activity IDs in that display order. A step can declare `dependsOn`
conditions for other named steps, forming an acyclic execution graph that
controls execution eligibility. Pipeline runs persist a frozen graph and select
one eligible Activity run at a time.

## Pipeline calls

| Method | Path | Description |
| ------ | ---- | ----------- |
| `GET` | `/api/v1/pipelines` | Lists ten filtered pipelines after an offset. |
| `POST` | `/api/v1/pipelines` | Creates an enabled pipeline. |
| `GET` | `/api/v1/pipelines/{pipeline_id}` | Describes one complete ordered definition. |
| `POST` | `/api/v1/pipelines/{pipeline_id}/runs` | Creates a pipeline run and selects its first Activity run. |
| `GET` | `/api/v1/pipelines/{pipeline_id}/runs/{run_id}` | Describes a pipeline run and selected Activity run. |
| `POST` | `/api/v1/pipelines/{pipeline_id}/runs/{run_id}/continue` | Records a terminal Activity result and selects the next eligible step. |
| `PATCH` | `/api/v1/pipelines/{pipeline_id}` | Updates mutable fields or enablement. |
| `DELETE` | `/api/v1/pipelines/{pipeline_id}` | Archives the pipeline. |
| `GET` | `/api/v1/pipelines/{pipeline_id}/changelog` | Lists ten newest changelog entries. |

Creation requires a non-empty `name`, a `description`, and at least one step.
New pipelines are enabled. PATCH accepts `name`, `description`, `enabled`, and
`steps`; supplying `steps` replaces the complete ordered array. Archived
pipelines are immutable and omitted from unfiltered listings.

Each step has a `dependsOn` array. Every item contains an `activity` name from
another step and a `condition` of `success` or `failure`. The array can be
empty. Dependency targets must be unambiguous and the graph cannot contain
cycles.

## Execute pipelines

`POST /api/v1/pipelines/{pipeline_id}/runs` accepts an `input` string used by
every scheduled Activity. The response includes `current_activity_run` while
the pipeline run is `in_progress`. The CLI executes that child run through its
existing local repository, filesystem, and Git checkpoints, then calls the
pipeline run's `continue` endpoint. The API evaluates `success` and `failure`
dependencies against the child result, skips impossible branches, and selects
the next eligible step in declared order. The pipeline completes after every
step is completed, failed, or skipped.

## List pipelines

`GET /api/v1/pipelines` returns ten pipelines after the optional non-negative
`offset`. `search` matches name and description case-insensitively, and
`status` accepts `active`, `disabled`, or `archived`. Each Pipeline resolves
every stored step to its full persisted Activity.

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
      "name": "ProductionReleaseReview",
      "description": "Review a release, collect readiness information, and request approval.",
      "enabled": true,
      "steps": [
        {
          "id": "activity-release-review",
          "workspace_id": "workspace-acme",
          "name": "ReviewReleasePlan",
          "dependsOn": [],
          "description": "Reach a shared decision about release readiness.",
          "status": "active",
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
          },
          "created_at": "2026-08-13T10:00:00Z",
          "created_by": "user-123",
          "updated_at": "2026-08-13T10:00:00Z",
          "updated_by": "user-123"
        },
        {
          "id": "activity-readiness-quiz",
          "workspace_id": "workspace-acme",
          "name": "DeploymentReadinessQuiz",
          "dependsOn": [
            {"activity": "ReviewReleasePlan", "condition": "success"}
          ],
          "description": "Confirm operational readiness before deployment.",
          "status": "active",
          "type": "quiz",
          "config": {
            "quiz": {
              "questions": []
            }
          },
          "created_at": "2026-08-13T10:00:00Z",
          "created_by": "user-123",
          "updated_at": "2026-08-13T10:00:00Z",
          "updated_by": "user-123"
        },
        {
          "id": "activity-production-approval",
          "workspace_id": "workspace-acme",
          "name": "ApproveProductionRelease",
          "dependsOn": [
            {"activity": "DeploymentReadinessQuiz", "condition": "success"},
            {"activity": "ReviewReleasePlan", "condition": "failure"}
          ],
          "description": "A release manager approves deployment.",
          "status": "active",
          "type": "approval",
          "config": {},
          "created_at": "2026-08-13T10:00:00Z",
          "created_by": "user-123",
          "updated_at": "2026-08-13T10:00:00Z",
          "updated_by": "user-123"
        }
      ],
      "created_at": "2026-08-13T10:00:00Z",
      "updated_at": "2026-08-13T10:00:00Z"
    }
  ],
  "total": 1
}
```

## Describe a pipeline

`GET /api/v1/pipelines/{pipeline_id}` returns the complete ordered definition
with the full persisted Activity for every step, including its generated ID.

```http
GET /api/v1/pipelines/pipeline-production-release-review
X-Workspace-ID: workspace-acme
```

Example response (`200 OK`):

```json
{
  "id": "pipeline-production-release-review",
  "name": "ProductionReleaseReview",
  "description": "Review a release, collect readiness information, and request approval.",
  "enabled": true,
  "steps": [
    {
      "id": "activity-release-review",
      "workspace_id": "workspace-acme",
      "name": "ReviewReleasePlan",
      "dependsOn": [],
      "description": "Reach a shared decision about release readiness.",
      "status": "active",
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
      },
      "created_at": "2026-08-13T10:00:00Z",
      "created_by": "user-123",
      "updated_at": "2026-08-13T10:00:00Z",
      "updated_by": "user-123"
    },
    {
      "id": "activity-readiness-quiz",
      "workspace_id": "workspace-acme",
      "name": "DeploymentReadinessQuiz",
      "dependsOn": [
        {"activity": "ReviewReleasePlan", "condition": "success"}
      ],
      "description": "Confirm operational readiness before deployment.",
      "status": "active",
      "type": "quiz",
      "config": {
        "quiz": {
          "questions": []
        }
      },
      "created_at": "2026-08-13T10:00:00Z",
      "created_by": "user-123",
      "updated_at": "2026-08-13T10:00:00Z",
      "updated_by": "user-123"
    },
    {
      "id": "activity-production-approval",
      "workspace_id": "workspace-acme",
      "name": "ApproveProductionRelease",
      "dependsOn": [
        {"activity": "DeploymentReadinessQuiz", "condition": "success"},
        {"activity": "ReviewReleasePlan", "condition": "failure"}
      ],
      "description": "A release manager approves deployment.",
      "status": "active",
      "type": "approval",
      "config": {},
      "created_at": "2026-08-13T10:00:00Z",
      "created_by": "user-123",
      "updated_at": "2026-08-13T10:00:00Z",
      "updated_by": "user-123"
    }
  ],
  "created_at": "2026-08-13T10:00:00Z",
  "updated_at": "2026-08-13T10:00:00Z"
}
```

## Create a pipeline

`POST /api/v1/pipelines` creates an enabled pipeline in the workspace supplied
by `X-Workspace-ID`. Supply complete Activity definitions in execution order.
The API validates and persists each Activity in the same transaction, assigns
each one an ID, and stores those IDs as Pipeline steps. The response resolves
each stored step to its full persisted Activity.

```http
POST /api/v1/pipelines
X-Workspace-ID: workspace-acme
Content-Type: application/json
```

```json
{
  "name": "ProductionReleaseReview",
  "description": "Review a release, collect readiness information, and request approval.",
  "steps": [
    {
      "name": "ReviewReleasePlan",
      "dependsOn": [],
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
      "name": "DeploymentReadinessQuiz",
      "dependsOn": [
        {"activity": "ReviewReleasePlan", "condition": "success"}
      ],
      "description": "Confirm operational readiness before deployment.",
      "type": "quiz",
      "config": {
        "quiz": {
          "questions": []
        }
      }
    },
    {
      "name": "ApproveProductionRelease",
      "dependsOn": [
        {"activity": "DeploymentReadinessQuiz", "condition": "success"},
        {"activity": "ReviewReleasePlan", "condition": "failure"}
      ],
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
  "name": "ProductionReleaseReview",
  "description": "Review a release, collect readiness information, and request approval.",
  "enabled": true,
  "steps": [
    {
      "id": "activity-release-review",
      "workspace_id": "workspace-acme",
      "name": "ReviewReleasePlan",
      "dependsOn": [],
      "description": "Reach a shared decision about release readiness.",
      "status": "active",
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
      },
      "created_at": "2026-08-13T10:00:00Z",
      "created_by": "user-123",
      "updated_at": "2026-08-13T10:00:00Z",
      "updated_by": "user-123"
    },
    {
      "id": "activity-readiness-quiz",
      "workspace_id": "workspace-acme",
      "name": "DeploymentReadinessQuiz",
      "dependsOn": [
        {"activity": "ReviewReleasePlan", "condition": "success"}
      ],
      "description": "Confirm operational readiness before deployment.",
      "status": "active",
      "type": "quiz",
      "config": {
        "quiz": {
          "questions": []
        }
      },
      "created_at": "2026-08-13T10:00:00Z",
      "created_by": "user-123",
      "updated_at": "2026-08-13T10:00:00Z",
      "updated_by": "user-123"
    },
    {
      "id": "activity-production-approval",
      "workspace_id": "workspace-acme",
      "name": "ApproveProductionRelease",
      "dependsOn": [
        {"activity": "DeploymentReadinessQuiz", "condition": "success"},
        {"activity": "ReviewReleasePlan", "condition": "failure"}
      ],
      "description": "A release manager approves deployment.",
      "status": "active",
      "type": "approval",
      "config": {},
      "created_at": "2026-08-13T10:00:00Z",
      "created_by": "user-123",
      "updated_at": "2026-08-13T10:00:00Z",
      "updated_by": "user-123"
    }
  ],
  "created_at": "2026-08-13T10:00:00Z",
  "updated_at": "2026-08-13T10:00:00Z"
}
```

## Update a pipeline

`PATCH /api/v1/pipelines/{pipeline_id}` accepts one or more of `name`,
`description`, `enabled`, and `steps`. Supplying `steps` replaces the complete
ordered array and creates new independent Activity records from the supplied
inline definitions. The response resolves every stored step to its full
persisted Activity.

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
  "name": "ProductionReleaseReview",
  "description": "Review a release, collect readiness information, and request approval.",
  "enabled": false,
  "steps": [
    {
      "id": "activity-release-review",
      "workspace_id": "workspace-acme",
      "name": "ReviewReleasePlan",
      "dependsOn": [],
      "description": "Reach a shared decision about release readiness.",
      "status": "active",
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
      },
      "created_at": "2026-08-13T10:00:00Z",
      "created_by": "user-123",
      "updated_at": "2026-08-13T10:00:00Z",
      "updated_by": "user-123"
    },
    {
      "id": "activity-readiness-quiz",
      "workspace_id": "workspace-acme",
      "name": "DeploymentReadinessQuiz",
      "dependsOn": [
        {"activity": "ReviewReleasePlan", "condition": "success"}
      ],
      "description": "Confirm operational readiness before deployment.",
      "status": "active",
      "type": "quiz",
      "config": {
        "quiz": {
          "questions": []
        }
      },
      "created_at": "2026-08-13T10:00:00Z",
      "created_by": "user-123",
      "updated_at": "2026-08-13T10:00:00Z",
      "updated_by": "user-123"
    },
    {
      "id": "activity-production-approval",
      "workspace_id": "workspace-acme",
      "name": "ApproveProductionRelease",
      "dependsOn": [
        {"activity": "DeploymentReadinessQuiz", "condition": "success"},
        {"activity": "ReviewReleasePlan", "condition": "failure"}
      ],
      "description": "A release manager approves deployment.",
      "status": "active",
      "type": "approval",
      "config": {},
      "created_at": "2026-08-13T10:00:00Z",
      "created_by": "user-123",
      "updated_at": "2026-08-13T10:00:00Z",
      "updated_by": "user-123"
    }
  ],
  "created_at": "2026-08-13T10:00:00Z",
  "updated_at": "2026-08-13T10:15:00Z"
}
```

The list accepts a non-negative `offset`, optional case-insensitive `search`
over name and description, and optional `status` of `active`, `disabled`, or
`archived`. Active pipelines sort before disabled and archived pipelines.

Every Pipeline response resolves each step to the complete Activity
representation. Pipeline creation and step replacement both accept the same
full Activity definition shape as `POST /api/v1/activities`. Replacing steps
creates new Activity records; it does not modify or delete Activities from
prior steps.

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
      "diff": {
        "enabled": {
          "from": true,
          "to": false
        }
      },
      "content": null
    }
  ],
  "total": 2
}
```

Request schema failures use the standard API error envelope. Invalid step
structures use `invalid_pipeline_steps`.
