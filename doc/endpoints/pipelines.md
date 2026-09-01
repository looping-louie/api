# Pipelines

A Pipeline is a User-owned declared sequence of Activity definitions. The API
creates an independent User-owned Activity record for every supplied step, then
stores the generated Activity IDs in that display order. Standalone Pipeline
definition routes use `X-User-ID` and ignore `X-Project-ID`. A step can
declare `dependsOn` conditions for other named steps, forming an acyclic
execution graph that controls execution eligibility. Pipeline run routes use
`X-Project-ID` to select the Project where the frozen graph executes and a
runtime worker claims one eligible Activity run at a time.

## Pipeline calls

| Method | Path | Description |
| ------ | ---- | ----------- |
| `GET` | `/api/v1/pipelines` | Lists ten filtered pipelines after an offset. |
| `POST` | `/api/v1/pipelines` | Creates an enabled pipeline. |
| `GET` | `/api/v1/pipelines/{pipeline_id}` | Describes one complete ordered definition. |
| `PATCH` | `/api/v1/pipelines/{pipeline_id}` | Updates mutable fields or enablement. |
| `DELETE` | `/api/v1/pipelines/{pipeline_id}` | Archives the pipeline. |
| `GET` | `/api/v1/pipelines/{pipeline_id}/changelog` | Lists ten newest changelog entries. |
| `GET` | `/api/v1/pipelines/{pipeline_id}/runs?claimable=true` | Lists claimable runs and their entity tags. |
| `POST` | `/api/v1/pipelines/{pipeline_id}/runs` | Creates a prepared pipeline run. |
| `POST` | `/api/v1/pipelines/{pipeline_id}/runs/{run_id}/start` | Starts a prepared pipeline run. |
| `PATCH` | `/api/v1/pipelines/{pipeline_id}/runs/{run_id}` | Conditionally claims one listed run for a worker. |
| `GET` | `/api/v1/pipelines/{pipeline_id}/runs/{run_id}` | Describes a pipeline run and selected Activity run. |
| `GET` | `/api/v1/pipelines/{pipeline_id}/runs/{run_id}/readiness` | Describes aggregate Worker readiness for a queued run. |
| `GET` | `/api/v1/pipelines/{pipeline_id}/runs/{run_id}/events` | Lists immutable Pipeline-run execution events. |
| `POST` | `/api/v1/pipelines/{pipeline_id}/runs/{run_id}/lease` | Renews an active worker lease for one minute. |
| `POST` | `/api/v1/pipelines/{pipeline_id}/runs/{run_id}/continue` | Records a terminal Activity result and selects the next eligible step. |

Creation requires a non-empty `name`, a `description`, and at least one step.
Pipelines persist nullable `model_id` and `harness` overrides. PATCH accepts
`name`, `description`, `enabled`, `steps`, `model_id`, and `harness`;
supplying `steps` replaces the complete ordered array. `null` clears either
override. PipelineRun creation resolves model IDs at agent, Activity, Pipeline,
then User scope. The `louie` Harness selects and freezes the first usable
Linked Service offering the effective model. Harnesses resolve
at Activity, Pipeline, then User scope. It freezes the effective values
in its Pipeline and Activity snapshots. An unset effective Harness retains the
legacy `louie` v1 compatibility behavior.
For every `codex_cli` Activity, creation resolves its generator Persona and the
Persona's ordered Skills from the current User library. It freezes their IDs,
versions, metadata, and content in the Activity snapshot returned later in the
child ActivityRun's `run_harness` payload. Subsequent Persona or Skill edits do
not alter an existing run. Creation also freezes the effective generator model
as `requested_model`; a missing effective model rejects the run instead of
falling back to the worker's local Codex configuration. Unknown, deprecated,
or User-disabled Codex models also reject creation before any PipelineRun is
persisted. These failures return `409 pipeline_run_unavailable` with
`details.reason`, `details.pipeline_id`, `details.activity_id`, and, when
known, `details.model_id` so clients can present an actionable configuration
error.
Archived pipelines are immutable and omitted from unfiltered listings.

Every Pipeline response includes top-level `model_id` and `harness` keys,
and every returned step includes its own Activity-level keys. Unset overrides
serialize as `null`; the repeated `null` fields are omitted from examples where
they are not relevant to the example.

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
| `model_id` | String or null | No | A logical catalog model ID. `null` means inherit. |
| `harness` | Object or null | No | An empty `louie` v1 or `codex_cli` v1 configuration. `null` means inherit. |
| `dependsOn` | Array | No | Defaults to an empty array. Every item names another unique step and uses a `success` or `failure` condition. The resulting graph must be acyclic. |

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
          "name": "ReviewReleasePlan",
          "dependsOn": [
          ],
          "description": "Reach a shared decision about release readiness.",
          "status": "active",
          "type": "roundtable_loop",
          "config": {
            "stop_conditions": {
              "max_iterations": 2
            },
            "agents": [
              {
                "model_id": "gpt-5",
                "persona_id": "release-manager",
                "role": "generator"},
              {
                "model_id": "gpt-5",
                "persona_id": "quality-engineer",
                "role": "generator"},
              {
                "model_id": "gpt-5",
                "persona_id": "technical-lead",
                "role": "aggregator"
              }
            ],
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
          "name": "DeploymentReadinessQuiz",
          "dependsOn": [
            {
              "activity": "ReviewReleasePlan",
              "condition": "success"
            }
          ],
          "description": "Confirm operational readiness before deployment.",
          "status": "active",
          "type": "quiz",
          "config": {
            "quiz": {
              "questions": [
              ]
            }
          },
          "created_at": "2026-08-13T10:00:00Z",
          "created_by": "user-123",
          "updated_at": "2026-08-13T10:00:00Z",
          "updated_by": "user-123"
        },
        {
          "id": "activity-production-approval",
          "name": "ApproveProductionRelease",
          "dependsOn": [
            {
              "activity": "DeploymentReadinessQuiz",
              "condition": "success"
            },
            {
              "activity": "ReviewReleasePlan",
              "condition": "failure"
            }
          ],
          "description": "A release manager approves deployment.",
          "status": "active",
          "type": "approval",
          "config": {
          },
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
X-User-ID: user-123
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
      "name": "ReviewReleasePlan",
      "dependsOn": [
      ],
      "description": "Reach a shared decision about release readiness.",
      "status": "active",
      "type": "roundtable_loop",
      "config": {
        "stop_conditions": {
          "max_iterations": 2
        },
        "agents": [
          {
            "model_id": "gpt-5",
            "persona_id": "release-manager",
            "role": "generator"
          },
          {
            "model_id": "gpt-5",
            "persona_id": "quality-engineer",
            "role": "generator"
          },
          {
            "model_id": "gpt-5",
            "persona_id": "technical-lead",
            "role": "aggregator"
          }
        ],
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
      "name": "DeploymentReadinessQuiz",
      "dependsOn": [
        {
          "activity": "ReviewReleasePlan",
          "condition": "success"
        }
      ],
      "description": "Confirm operational readiness before deployment.",
      "status": "active",
      "type": "quiz",
      "config": {
        "quiz": {
          "questions": [
          ]
        }
      },
      "created_at": "2026-08-13T10:00:00Z",
      "created_by": "user-123",
      "updated_at": "2026-08-13T10:00:00Z",
      "updated_by": "user-123"
    },
    {
      "id": "activity-production-approval",
      "name": "ApproveProductionRelease",
      "dependsOn": [
        {
          "activity": "DeploymentReadinessQuiz",
          "condition": "success"
        },
        {
          "activity": "ReviewReleasePlan",
          "condition": "failure"
        }
      ],
      "description": "A release manager approves deployment.",
      "status": "active",
      "type": "approval",
      "config": {
      },
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

`POST /api/v1/pipelines` creates an enabled Pipeline for the User supplied by
`X-User-ID` and ignores `X-Project-ID`. Supply complete Activity definitions
in execution order. The API validates and persists each Activity in the same
transaction, assigns each one an ID, and stores those IDs as Pipeline steps. The
response resolves each stored step to its full persisted Activity.

### Create Request Properties

| Property | JSON type | Required | Restrictions |
| -------- | --------- | -------- | ------------ |
| `name` | String | Yes | Contains 1 to 140 characters. Starts with a Unicode letter, number, or `_`. Does not contain whitespace, `.`, `+`, `?`, `/`, `<`, `>`, `*`, `%`, `&`, or `:`. |
| `description` | String | Yes | May be empty. |
| `steps` | Array of Activity definitions | Yes | Contains at least one step and uses the [Pipeline Step Schema](#pipeline-step-schema). |
| `model_id` | String or null | No | A logical catalog model ID. `null` means inherit. |
| `harness` | Object or null | No | Empty `louie` v1 and `codex_cli` v1 configurations are accepted. `null` means inherit. |

```http
POST /api/v1/pipelines
X-User-ID: user-123
Content-Type: application/json
```

```json
{
  "name": "ProductionReleaseReview",
  "description": "Review a release, collect readiness information, and request approval.",
  "steps": [
    {
      "name": "ReviewReleasePlan",
      "dependsOn": [
      ],
      "description": "Reach a shared decision about release readiness.",
      "type": "roundtable_loop",
      "config": {
        "stop_conditions": {
          "max_iterations": 2
        },
        "agents": [
          {
            "model_id": "gpt-5",
            "persona_id": "release-manager",
            "role": "generator"
          },
          {
            "model_id": "gpt-5",
            "persona_id": "quality-engineer",
            "role": "generator"
          },
          {
            "model_id": "gpt-5",
            "persona_id": "technical-lead",
            "role": "aggregator"
          }
        ],
        "output_contract": {
          "type": "text",
          "description": "Release decision."
        }
      }
    },
    {
      "name": "DeploymentReadinessQuiz",
      "dependsOn": [
        {
          "activity": "ReviewReleasePlan",
          "condition": "success"
        }
      ],
      "description": "Confirm operational readiness before deployment.",
      "type": "quiz",
      "config": {
        "quiz": {
          "questions": [
          ]
        }
      }
    },
    {
      "name": "ApproveProductionRelease",
      "dependsOn": [
        {
          "activity": "DeploymentReadinessQuiz",
          "condition": "success"
        },
        {
          "activity": "ReviewReleasePlan",
          "condition": "failure"
        }
      ],
      "description": "A release manager approves deployment.",
      "type": "approval",
      "config": {
      }
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
      "name": "ReviewReleasePlan",
      "dependsOn": [
      ],
      "description": "Reach a shared decision about release readiness.",
      "status": "active",
      "type": "roundtable_loop",
      "config": {
        "stop_conditions": {
          "max_iterations": 2
        },
        "agents": [
          {
            "model_id": "gpt-5",
            "persona_id": "release-manager",
            "role": "generator"
          },
          {
            "model_id": "gpt-5",
            "persona_id": "quality-engineer",
            "role": "generator"
          },
          {
            "model_id": "gpt-5",
            "persona_id": "technical-lead",
            "role": "aggregator"
          }
        ],
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
      "name": "DeploymentReadinessQuiz",
      "dependsOn": [
        {
          "activity": "ReviewReleasePlan",
          "condition": "success"
        }
      ],
      "description": "Confirm operational readiness before deployment.",
      "status": "active",
      "type": "quiz",
      "config": {
        "quiz": {
          "questions": [
          ]
        }
      },
      "created_at": "2026-08-13T10:00:00Z",
      "created_by": "user-123",
      "updated_at": "2026-08-13T10:00:00Z",
      "updated_by": "user-123"
    },
    {
      "id": "activity-production-approval",
      "name": "ApproveProductionRelease",
      "dependsOn": [
        {
          "activity": "DeploymentReadinessQuiz",
          "condition": "success"
        },
        {
          "activity": "ReviewReleasePlan",
          "condition": "failure"
        }
      ],
      "description": "A release manager approves deployment.",
      "status": "active",
      "type": "approval",
      "config": {
      },
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
`description`, `enabled`, `steps`, `model_id`, and `harness`. Supplying
`steps` replaces the complete ordered array and creates new independent Activity
records from the supplied inline definitions. Setting `model_id` or
`harness` to `null` clears that override. The response resolves every stored
step to its full persisted Activity.

### Update Request Properties

At least one property is required.

| Property | JSON type | Restrictions |
| -------- | --------- | ------------ |
| `name` | String | Contains 1 to 140 characters. Starts with a Unicode letter, number, or `_`. Does not contain whitespace, `.`, `+`, `?`, `/`, `<`, `>`, `*`, `%`, `&`, or `:`. |
| `description` | String | May be empty. |
| `enabled` | Boolean | Enables or disables the Pipeline. |
| `steps` | Array of Activity definitions | Contains at least one step, uses the [Pipeline Step Schema](#pipeline-step-schema), and replaces the complete ordered step collection. |
| `model_id` | String or null | A logical catalog model ID. `null` clears the override. |
| `harness` | Object or null | An empty `louie` v1 or `codex_cli` v1 configuration. `null` clears the override. |

```http
PATCH /api/v1/pipelines/pipeline-production-release-review
X-User-ID: user-123
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
      "name": "ReviewReleasePlan",
      "dependsOn": [
      ],
      "description": "Reach a shared decision about release readiness.",
      "status": "active",
      "type": "roundtable_loop",
      "config": {
        "stop_conditions": {
          "max_iterations": 2
        },
        "agents": [
          {
            "model_id": "gpt-5",
            "persona_id": "release-manager",
            "role": "generator"
          },
          {
            "model_id": "gpt-5",
            "persona_id": "quality-engineer",
            "role": "generator"
          },
          {
            "model_id": "gpt-5",
            "persona_id": "technical-lead",
            "role": "aggregator"
          }
        ],
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
      "name": "DeploymentReadinessQuiz",
      "dependsOn": [
        {
          "activity": "ReviewReleasePlan",
          "condition": "success"
        }
      ],
      "description": "Confirm operational readiness before deployment.",
      "status": "active",
      "type": "quiz",
      "config": {
        "quiz": {
          "questions": [
          ]
        }
      },
      "created_at": "2026-08-13T10:00:00Z",
      "created_by": "user-123",
      "updated_at": "2026-08-13T10:00:00Z",
      "updated_by": "user-123"
    },
    {
      "id": "activity-production-approval",
      "name": "ApproveProductionRelease",
      "dependsOn": [
        {
          "activity": "DeploymentReadinessQuiz",
          "condition": "success"
        },
        {
          "activity": "ReviewReleasePlan",
          "condition": "failure"
        }
      ],
      "description": "A release manager approves deployment.",
      "status": "active",
      "type": "approval",
      "config": {
      },
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

## Archive a pipeline

`DELETE /api/v1/pipelines/{pipeline_id}` archives a Pipeline and returns
the deletion response shown below. Archival is terminal: archived Pipelines reject PATCH
requests and are omitted from unfiltered listings. Existing Pipeline runs retain
their frozen graph and execution history.

```http
DELETE /api/v1/pipelines/pipeline-production-release-review
X-User-ID: user-123
```

Example response (`200 OK`):

```json
{
  "deleted": true
}
```

## List pipeline changelog entries

`GET /api/v1/pipelines/{pipeline_id}/changelog` returns ten newest entries
after the optional non-negative `offset`.

```http
GET /api/v1/pipelines/pipeline-production-release-review/changelog?offset=0
X-User-ID: user-123
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

## Execution Model

A Pipeline is a reusable graph definition. A PipelineRun is one requested
execution of its frozen graph. Each scheduled step creates an ActivityRun owned
by that PipelineRun; an ActivityRun is not an independently runnable workflow.

| Resource | Responsibility |
| -------- | -------------- |
| Pipeline | Reusable graph definition. An active Pipeline may create runs. |
| PipelineRun | One execution request, including frozen input, dependency graph, and commit mode. |
| ActivityRun | One child execution selected by its owning PipelineRun. |

The runtime is a pull-based executor. It polls the API for eligible Pipeline
runs and attempts ETag-protected claims; the API admits or rejects each claim.
The CLI is a control-plane client. It creates, starts, inspects, and operates
Pipeline runs, but it does not select a checkout or perform filesystem or Git
operations.

Human Activities are normal ActivityRuns with the `human` executor. Runtime
workers do not claim them. A dependency-ready human ActivityRun places its
PipelineRun in `waiting` until a user submits the human decision checkpoint.

### Lifecycle

```text
prepared -> queued -> claimed -> in_progress -> completed
                      |             |
                      |             -> waiting (human ActivityRun)
                      |
                      -> queued again when a lease expires
```

Creating a PipelineRun produces a `prepared` execution with
frozen input, steps, and commit policy. An explicit operator action transitions
it to `queued`, making runtime-owned work eligible for polling and claims. If
the first dependency-ready step has a human executor, the API instead creates
its waiting human ActivityRun without exposing the PipelineRun to workers.

The corresponding CLI commands are:

```text
ll pipelines runs create PIPELINE_ID --input "..."
  -> create a prepared PipelineRun

ll pipelines runs start PIPELINE_ID RUN_ID
  -> transition the PipelineRun from prepared to queued
```

Workers remain independent pollers; an operator does not direct a specific
worker to accept a claim.

Activity definitions remain reusable but are not directly callable. Retrying
execution is a PipelineRun-level operation because it needs the frozen graph,
input, commit mode, configured runtime checkout, and correction history. A
future `retry` command should create a new prepared PipelineRun rather than
altering completed ActivityRuns. Any future restart-from-step operation must
define its dependency reset and reuse semantics explicitly.

## Execute pipelines

`POST /api/v1/pipelines/{pipeline_id}/runs` accepts an `input` string used by
every scheduled Activity and a run-level `commit_mode`. The API freezes the
Pipeline graph and commit policy, then returns a `prepared` run. Creation does
not start repository execution or allocate an ActivityRun. Use the start
operation to make the run eligible for its assigned executor. `allow` is the
default mode. `forbid` leaves successfully applied and approved changes
uncommitted, and the API never schedules a commit checkpoint for that run.

Creation validates every frozen execution dependency before persistence. For
`codex_cli`, the effective generator model must exist, be active, and be enabled
by the current User's policy. Worker liveness and local Codex authentication are
not creation prerequisites: after start, a valid run remains `queued` until an
active worker heartbeat advertises the frozen Harness.

| Property | JSON type | Required | Restrictions |
| -------- | --------- | -------- | ------------ |
| `input` | String | Yes | Used by every scheduled Activity. |
| `commit_mode` | String | No | `allow` (default) or `forbid`. |

```http
POST /api/v1/pipelines/pipeline-production-release-review/runs
X-Project-ID: project-acme
Content-Type: application/json
```

```json
{
  "input": "Review the release candidate and determine whether it is ready for production.",
  "commit_mode": "allow"
}
```

Example response (`201 Created`):

```json
{
  "id": "pipeline-run-001",
  "pipeline_id": "pipeline-production-release-review",
  "input": "Review the release candidate and determine whether it is ready for production.",
  "commit_mode": "allow",
  "status": "prepared",
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

## Start a pipeline run

`POST /api/v1/pipelines/{pipeline_id}/runs/{run_id}/start` transitions a
`prepared` PipelineRun to `queued` when its next dependency-ready step has a
runtime executor. The runtime can then discover and conditionally claim it.

When the next ready step has a human executor, start creates that ActivityRun
and returns the PipelineRun in `waiting`; it never becomes runtime claimable.
Starting a run that is not `prepared` returns `409 pipeline_run_unavailable`.

## List claimable pipeline runs

The runtime first lists active Pipelines, then requests claimable runs beneath
each Pipeline. `GET /api/v1/pipelines/{pipeline_id}/runs?claimable=true`
returns queued runs and claimed runs whose lease has expired. The API owns that
decision; callers must not infer claimability from a raw persisted status.

```http
GET /api/v1/pipelines/pipeline-production-release-review/runs?claimable=true
X-Project-ID: project-acme
```

Example response (`200 OK`):

```json
{
  "items": [
    {
      "etag": "\"c1e5185f48a77b2f\"",
      "run": {
        "id": "pipeline-run-001",
        "pipeline_id": "pipeline-production-release-review",
        "input": "Review the release candidate and determine whether it is ready for production.",
        "commit_mode": "allow",
        "status": "queued",
        "current_activity_run": null,
        "steps": [
          {
            "activity_id": "activity-release-review",
            "status": "pending",
            "activity_run_id": null
          }
        ],
        "created_at": "2026-08-18T10:00:00Z",
        "created_by": "user-123",
        "updated_at": "2026-08-18T10:00:00Z"
      }
    }
  ],
  "total": 1
}
```

`etag` is opaque. The runtime sends it unchanged as the standard HTTP
`If-Match` request header when it attempts to claim that exact run. A Pipeline
with no claimable work returns an empty `items` array and `total` of `0`.

## Claim a pipeline run

`PATCH /api/v1/pipelines/{pipeline_id}/runs/{run_id}` atomically claims the
named listed run when its `If-Match` entity tag is still current. The request
requires the worker's stable `worker_id` and the only accepted target status,
`claimed`. On success, the API creates or resumes the selected Activity child,
issues a one-minute lease, and returns its secret `lease_token`. Pipeline runs
whose next ready step is an `approval` or `quiz` Activity are scheduled as
waiting human-owned Activity runs by the API and do not appear in the runtime
claimable-run list.

```http
PATCH /api/v1/pipelines/pipeline-production-release-review/runs/pipeline-run-001
X-Project-ID: project-acme
If-Match: "c1e5185f48a77b2f"
Content-Type: application/json
```

```json
{
  "worker_id": "runtime-local-01",
  "status": "claimed"
}
```

Example response (`200 OK`):

```json
{
  "run": {
    "id": "pipeline-run-001",
    "pipeline_id": "pipeline-production-release-review",
    "input": "Review the release candidate and determine whether it is ready for production.",
    "commit_mode": "allow",
    "status": "claimed",
    "current_activity_run": {
      "id": "activity-run-001",
      "activity_id": "activity-release-review",
      "input": "Review the release candidate and determine whether it is ready for production.",
      "status": "in_progress",
      "state": "awaiting_snapshot",
      "next_action": "collect_snapshot",
      "iteration": 1,
      "token_revision": 0,
      "continuation_token": "activity-continuation-token",
      "created_at": "2026-08-18T10:01:00Z",
      "created_by": "user-123",
      "updated_at": "2026-08-18T10:01:00Z",
      "payload": {
      }
    },
    "steps": [
      {
        "activity_id": "activity-release-review",
        "status": "in_progress",
        "activity_run_id": "activity-run-001"
      }
    ],
    "created_at": "2026-08-18T10:00:00Z",
    "created_by": "user-123",
    "updated_at": "2026-08-18T10:01:00Z"
  },
  "lease_token": "runtime-lease-token"
}
```

The worker must treat `lease_token` as secret and supply it to every lease,
Activity checkpoint, and Pipeline continuation request for the claim. A worker
cannot claim a disabled or archived Pipeline. If another worker changes the run
after it was listed, the API returns `412 pipeline_run_precondition_failed`; the
runtime discards that stale candidate and continues with another candidate or a
later poll.

## Describe a pipeline run

`GET /api/v1/pipelines/{pipeline_id}/runs/{run_id}` returns one durable
Pipeline execution and its currently selected Activity child. A terminal run
has `current_activity_run: null`; its `steps` retain the final outcome of every
frozen Pipeline step.

An approval or quiz step remains the current Activity run while the Pipeline
status is `waiting`. Its snapshot identifies the human executor and its
continuation action is `submit_human_decision`.

```http
GET /api/v1/pipelines/pipeline-production-release-review/runs/pipeline-run-001
X-Project-ID: project-acme
```

Example response (`200 OK`):

```json
{
  "id": "pipeline-run-001",
  "pipeline_id": "pipeline-production-release-review",
  "input": "Review the release candidate and determine whether it is ready for production.",
  "commit_mode": "forbid",
  "status": "completed",
  "current_activity_run": null,
  "steps": [
    {
      "activity_id": "activity-release-review",
      "status": "completed",
      "activity_run_id": "activity-run-001"
    }
  ],
  "created_at": "2026-08-18T10:00:00Z",
  "created_by": "user-123",
  "updated_at": "2026-08-18T10:05:00Z"
}
```

The API returns `404 pipeline_run_not_found` when the supplied run does not
belong to the Pipeline in the selected workspace.

## Describe pipeline run readiness

`GET /api/v1/pipelines/{pipeline_id}/runs/{run_id}/readiness` diagnoses a
queued run without exposing Worker identities or local configuration. The API
resolves the next claimable Activity's frozen Harness and applies the same
two-minute heartbeat window used by claim admission. The response distinguishes
no registrations, only stale registrations, active incompatible Workers, and
an active compatible Worker. A later compatible heartbeat changes the result
to `ready`; no user retry is required for the runtime to claim the run.

```http
GET /api/v1/pipelines/pipeline-production-release-review/runs/pipeline-run-001/readiness
X-Project-ID: project-acme
```

```json
{
  "status": "no_compatible_workers",
  "project_id": "project-acme",
  "required_harness": {
    "kind": "codex_cli",
    "version": "v1",
    "config": {}
  },
  "registered_worker_count": 2,
  "active_worker_count": 1,
  "compatible_worker_count": 0,
  "latest_heartbeat_at": "2026-08-21T10:00:00Z",
  "observed_at": "2026-08-21T10:00:30Z"
}
```

For non-queued runs, `status` is `not_applicable`, `required_harness` is null,
and the counts are zero. This race-safe response lets a client stop presenting
queued diagnostics after the run has already been claimed.

## List pipeline run events

`GET /api/v1/pipelines/{pipeline_id}/runs/{run_id}/events` returns the
append-only event ledger in creation order. Each entry has an ID, event type,
optional Activity ID, actor ID, JSON payload, and creation time. The API emits
`pipeline_run_created`, `pipeline_run_claimed`, `pipeline_step_started`,
`pipeline_step_completed`, and `pipeline_step_failed`. Harness children also
emit `harness_turn_completed` or `harness_turn_failed` with the normalized
Harness observation, including its v1 schema and frozen Harness identity plus
partial observations from failed processes. Consumers discriminate the
embedded observation by `payload.harness.kind`. Existing ledgers may still
contain the legacy `codex_turn_completed` and `codex_turn_failed` names. Human
decisions are regular Activity-run checkpoints, not Pipeline-run gate events.

## Complete a human Activity run

Submit an approval or quiz decision through the Activity-run continuation
endpoint. The request carries the current continuation token and an idempotency
key, but no worker lease token.

```json
{
  "continuation_token": "activity-continuation-token",
  "idempotency_key": "review-decision-001",
  "result": {
    "action": "submit_human_decision",
    "decision": "approved",
    "comment": "Ready to release."
  }
}
```

After a terminal human result, call Pipeline continuation with no lease token
to schedule the next step. A rejected decision resets the rejected step and
its transitive predecessors to `pending` for corrective execution. Once those
predecessors finish, the scheduler creates a new human Activity run.

## Renew a pipeline run lease

`POST /api/v1/pipelines/{pipeline_id}/runs/{run_id}/lease` extends an active
claim by one minute. Only the worker holding the current unexpired lease token
can renew it.

```http
POST /api/v1/pipelines/pipeline-production-release-review/runs/pipeline-run-001/lease
X-Project-ID: project-acme
Content-Type: application/json
```

```json
{
  "lease_token": "runtime-lease-token"
}
```

Example response (`200 OK`):

```json
{
  "lease_expires_at": "2026-08-18T10:02:00Z"
}
```

A missing, stale, or expired token returns `409 pipeline_run_unavailable`.

## Continue a pipeline run

`POST /api/v1/pipelines/{pipeline_id}/runs/{run_id}/continue` records the
selected terminal Activity child outcome and schedules the next dependency-ready
step. The worker calls this only after an Activity checkpoint response is
terminal.

```http
POST /api/v1/pipelines/pipeline-production-release-review/runs/pipeline-run-001/continue
X-Project-ID: project-acme
Content-Type: application/json
```

```json
{
  "lease_token": "runtime-lease-token"
}
```

Example response (`200 OK`):

```json
{
  "id": "pipeline-run-001",
  "pipeline_id": "pipeline-production-release-review",
  "input": "Review the release candidate and determine whether it is ready for production.",
  "commit_mode": "allow",
  "status": "in_progress",
  "current_activity_run": {
    "id": "activity-run-002",
    "activity_id": "activity-readiness-quiz",
    "input": "Review the release candidate and determine whether it is ready for production.",
    "status": "in_progress",
    "state": "awaiting_snapshot",
    "next_action": "collect_snapshot",
    "iteration": 1,
    "token_revision": 0,
    "continuation_token": "activity-continuation-token",
    "created_at": "2026-08-18T10:03:00Z",
    "created_by": "user-123",
    "updated_at": "2026-08-18T10:03:00Z",
    "payload": {
    }
  },
  "steps": [
    {
      "activity_id": "activity-release-review",
      "status": "completed",
      "activity_run_id": "activity-run-001"
    },
    {
      "activity_id": "activity-readiness-quiz",
      "status": "in_progress",
      "activity_run_id": "activity-run-002"
    }
  ],
  "created_at": "2026-08-18T10:00:00Z",
  "created_by": "user-123",
  "updated_at": "2026-08-18T10:03:00Z"
}
```

When no eligible step remains, the response has `current_activity_run: null`
and a terminal `completed` or `failed` status. A missing, stale, or expired
lease token returns `409 pipeline_run_unavailable`.
