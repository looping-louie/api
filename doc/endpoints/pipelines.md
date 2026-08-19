# Pipelines

A pipeline stores a declared sequence of Activity definitions. The API creates
an independent persisted Activity record for every supplied step, then stores
the generated Activity IDs in that display order. A step can declare `dependsOn`
conditions for other named steps, forming an acyclic execution graph that
controls execution eligibility. Pipeline runs persist a frozen graph and wait
for a runtime worker to claim and select one eligible Activity run at a time.

## Pipeline calls

| Method | Path | Description |
| ------ | ---- | ----------- |
| `GET` | `/api/v1/pipelines` | Lists ten filtered pipelines after an offset. |
| `POST` | `/api/v1/pipelines` | Creates an enabled pipeline. |
| `GET` | `/api/v1/pipelines/{pipeline_id}` | Describes one complete ordered definition. |
| `POST` | `/api/v1/pipelines/{pipeline_id}/runs` | Queues a pipeline run for a runtime worker. |
| `POST` | `/api/v1/pipelines/runs/claim` | Atomically claims the next queued workspace run for a worker. |
| `GET` | `/api/v1/pipelines/{pipeline_id}/runs/{run_id}` | Describes a pipeline run and selected Activity run. |
| `POST` | `/api/v1/pipelines/{pipeline_id}/runs/{run_id}/continue` | Records a terminal Activity result and selects the next eligible step. |
| `PATCH` | `/api/v1/pipelines/{pipeline_id}` | Updates mutable fields or enablement. |
| `DELETE` | `/api/v1/pipelines/{pipeline_id}` | Archives the pipeline. |
| `GET` | `/api/v1/pipelines/{pipeline_id}/changelog` | Lists ten newest changelog entries. |

Creation requires a non-empty `name`, a `description`, and at least one step.
New pipelines are enabled. PATCH accepts `name`, `description`, `enabled`, and
`steps`; supplying `steps` replaces the complete ordered array. Archived
pipelines are immutable and omitted from unfiltered listings.

## Pipeline Step Schema

Every item in `steps` uses the Activity definition schema. Its `name` follows
the same name restrictions as the Pipeline name. Each item can also contain a
`dependsOn` array.

| Step property | JSON type | Required | Restrictions |
| ------------- | --------- | -------- | ------------ |
| `name` | String | Yes | Uses the shared Activity and Pipeline name format. Must be unique within this Pipeline when referenced by `dependsOn`. |
| `description` | String | Yes | May be empty. |
| `type` | String | Yes | One of `approval`, `quiz`, `direct_loop`, `refinement_loop`, or `roundtable_loop`. |
| `config` | Object | Yes | Matches the selected Activity type. |
| `dependsOn` | Array | No | Defaults to `[]`. Every item names another unique step and uses a `success` or `failure` condition. The resulting graph must be acyclic. |

Each step has a `dependsOn` array. Every item contains an `activity` name from
another step and a `condition` of `success` or `failure`. The array can be
empty. Dependency targets must be unambiguous and the graph cannot contain
cycles.

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

### Create Request Properties

| Property | JSON type | Required | Restrictions |
| -------- | --------- | -------- | ------------ |
| `name` | String | Yes | Contains 1 to 140 characters. Starts with a Unicode letter, number, or `_`. Does not contain whitespace, `.`, `+`, `?`, `/`, `<`, `>`, `*`, `%`, `&`, or `:`. |
| `description` | String | Yes | May be empty. |
| `steps` | Array of Activity definitions | Yes | Contains at least one step and uses the [Pipeline Step Schema](#pipeline-step-schema). |

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

### Update Request Properties

At least one property is required.

| Property | JSON type | Restrictions |
| -------- | --------- | ------------ |
| `name` | String | Contains 1 to 140 characters. Starts with a Unicode letter, number, or `_`. Does not contain whitespace, `.`, `+`, `?`, `/`, `<`, `>`, `*`, `%`, `&`, or `:`. |
| `description` | String | May be empty. |
| `enabled` | Boolean | Enables or disables the Pipeline. |
| `steps` | Array of Activity definitions | Contains at least one step, uses the [Pipeline Step Schema](#pipeline-step-schema), and replaces the complete ordered step collection. |

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

## Execute pipelines

`POST /api/v1/pipelines/{pipeline_id}/runs` accepts an `input` string used by
every scheduled Activity. The API freezes the Pipeline graph and returns a
`queued` run. Creation does not allocate an Activity run or start repository
execution.

```http
POST /api/v1/pipelines/pipeline-production-release-review/runs
X-Workspace-ID: workspace-acme
Content-Type: application/json
```

```json
{
  "input": "Review the release candidate and determine whether it is ready for production."
}
```

Example response (`201 Created`):

```json
{
  "id": "pipeline-run-001",
  "pipeline_id": "pipeline-production-release-review",
  "input": "Review the release candidate and determine whether it is ready for production.",
  "status": "queued",
  "current_activity_run": null,
  "steps": [
    {
      "activity_id": "activity-release-review",
      "status": "pending",
      "activity_run_id": null
    },
    {
      "activity_id": "activity-readiness-quiz",
      "status": "pending",
      "activity_run_id": null
    },
    {
      "activity_id": "activity-production-approval",
      "status": "pending",
      "activity_run_id": null
    }
  ],
  "created_at": "2026-08-18T10:00:00Z",
  "created_by": "user-123",
  "updated_at": "2026-08-18T10:00:00Z"
}
```

## Claim queued pipeline run

`POST /api/v1/pipelines/runs/claim` atomically assigns the oldest queued or
lease-expired run in the selected workspace to a runtime worker. The request
requires the worker's stable `worker_id`. The response contains a lease token,
which is returned only to the worker that successfully claimed the run.

```http
POST /api/v1/pipelines/runs/claim
X-Workspace-ID: workspace-acme
Content-Type: application/json
```

```json
{
  "worker_id": "runtime-local-01"
}
```

When work is available, the API returns `200 OK` with a `claimed` run, the
initial `current_activity_run`, and a `lease_token`. A claim expires after one
minute. When no run is available, the API returns `204 No Content`.

The runtime executes `current_activity_run` through its local repository,
filesystem, and Git checkpoints. After that child reaches a terminal state,
call `POST /api/v1/pipelines/{pipeline_id}/runs/{run_id}/continue` without a
request body. The API evaluates `success` and `failure` dependencies, skips
impossible branches, and selects the next eligible step in declared order.

```http
POST /api/v1/pipelines/pipeline-production-release-review/runs/pipeline-run-001/continue
X-Workspace-ID: workspace-acme
```

The response is another Pipeline Run representation. It contains the next
`current_activity_run` when work remains, or `null` after every step has been
completed, failed, or skipped.
