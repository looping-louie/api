# Activities

Activities are workspace-scoped, possibly reusable units of work. They can be
created directly or generated when an inline definition is supplied while
creating or updating a Pipeline. The current supported types are `approval`,
`quiz`, `direct_loop`, `refinement_loop`, and `roundtable_loop`. Approval
activities represent human approval, and quiz activities collect human quiz
responses. Direct, refinement, and roundtable loop activities can create
persisted runs. Refinement runs add reviewer approval and retry checkpoints
after local application. Approval and quiz execution are reserved for future
pipeline orchestration.

## Resource endpoints

| Method | Path | Purpose |
| ------ | ---- | ------- |
| `GET` | `/api/v1/activities` | List activities. |
| `POST` | `/api/v1/activities` | Create an activity. |
| `GET` | `/api/v1/activities/{activity_id}` | Describe an activity. |
| `PATCH` | `/api/v1/activities/{activity_id}` | Update an activity. |
| `DELETE` | `/api/v1/activities/{activity_id}` | Delete an activity. |
| `GET` | `/api/v1/activities/{activity_id}/changelog` | List activity history. |

Activity creation specifies the sole `type` discriminator. `config` does not
include a `type` field; its required shape is selected by the top-level type.
The activity type is immutable after creation, and PATCH validates replacement
configurations against the persisted activity type.

Activities also accept nullable top-level `model_target` and `harness`
overrides. Loop agents accept nullable `model_target` values in addition to
their retained legacy `model_id`. A model target always contains both
`linked_service_id` and `model_id`; the API validates it against the selected
workspace's available Linked Service. `null` clears an Activity override.
PipelineRun creation resolves an Activity model target before Pipeline and
Workspace candidates, and resolves an Activity Harness before Pipeline and
Workspace candidates. The resolved values are frozen into the child
ActivityRun snapshot. An agent target takes precedence over the resolved
Activity target; an agent with no resolved target retains legacy Persona
routing.

Every Activity response includes top-level `model_target` and `harness` keys,
with `null` for an unset override. The type-specific response examples below
omit those repeated `null` fields unless an override is relevant.

## Activity Definition Schema

`POST /api/v1/activities` accepts the following JSON properties. `PATCH`
accepts the mutable properties marked as optional; it rejects an empty request.

| Property | JSON type | Create | Update | Restrictions |
| -------- | --------- | ------ | ------ | ------------ |
| `name` | String | Required | Optional | Contains 1 to 140 characters. Starts with a Unicode letter, number, or `_`. Does not contain whitespace, `.`, `+`, `?`, `/`, `<`, `>`, `*`, `%`, `&`, or `:`. |
| `description` | String | Required | Optional | May be empty. |
| `type` | String | Required | Not allowed | One of `approval`, `quiz`, `direct_loop`, `refinement_loop`, or `roundtable_loop`. Immutable after creation. |
| `config` | Object | Required | Optional | Shape is selected by `type`. Does not contain a nested `type` property. |
| `model_target` | Object or null | Optional | Optional | A linked service and model pair. `null` clears the override. |
| `harness` | Object or null | Optional | Optional | An empty `louie` v1 or `codex_cli` v1 configuration. `null` clears the override. |
| `status` | String | Not allowed | Optional | One of `active`, `disabled`, or `archived`. |

The following table describes the required `config` shape for every Activity
type.

| Activity type | Required `config` properties | Restrictions |
| ------------- | ---------------------------- | ------------ |
| `approval` | None | `config` must be an empty object. |
| `quiz` | `quiz` | `quiz` is an object containing the quiz definition. |
| `direct_loop` | `stop_conditions`, `agents`, `output_contract` | Exactly one generator; no reviewer or aggregator. |
| `refinement_loop` | `stop_conditions`, `agents`, `output_contract` | Exactly one generator, at least one reviewer, and no aggregator. |
| `roundtable_loop` | `stop_conditions`, `agents`, `output_contract` | At least two generators, exactly one aggregator, and no reviewer. |

Every loop agent requires a `persona_id` and `role`. An explicit agent
`model_target` is validated as a linked-service/model pair. Without one, the
legacy Persona selection behavior remains available; `model_id` is retained for
compatibility until Persona routing is removed.

## Activity runs

Pipeline scheduling creates persisted ActivityRuns for dependency-ready steps.
`/api/v1/activities/{activity_id}/runs` exposes those Pipeline-owned runs for
display and execution continuation; it cannot create standalone executions.
Each run response identifies its owning definition with `activity_id`; it does
not expose a legacy loop identifier.

## List activities

`GET /api/v1/activities` returns ten activities after the optional
non-negative `offset`.

```http
GET /api/v1/activities?offset=0
X-Workspace-ID: workspace-acme
```

Example response (`200 OK`):

```json
{
  "items": [
    {
      "id": "activity-implementation",
      "workspace_id": "workspace-acme",
      "name": "ImplementRequestedChange",
      "description": "Make and validate a focused code change.",
      "status": "active",
      "type": "direct_loop",
      "config": {
        "stop_conditions": {
          "max_iterations": 3,
          "max_tokens": 12000
        },
        "agents": [
          {
            "model_id": "gpt-5",
            "persona_id": "software-engineer",
            "role": "generator"
          }
        ],
        "output_contract": {
          "type": "text",
          "description": "A concise implementation summary and validation result."
        }
      },
      "created_at": "2026-08-13T10:00:00Z",
      "created_by": "user-123",
      "updated_at": "2026-08-13T10:00:00Z",
      "updated_by": "user-123"
    }
  ],
  "total": 1
}
```

## Describe an activity

`GET /api/v1/activities/{activity_id}` returns the complete Activity,
including its type-specific configuration.

```http
GET /api/v1/activities/activity-implementation
X-Workspace-ID: workspace-acme
```

Example response (`200 OK`):

```json
{
  "id": "activity-implementation",
  "workspace_id": "workspace-acme",
  "name": "ImplementRequestedChange",
  "description": "Make and validate a focused code change.",
  "status": "active",
  "type": "direct_loop",
  "config": {
    "stop_conditions": {
      "max_iterations": 3,
      "max_tokens": 12000
    },
    "agents": [
      {
        "model_id": "gpt-5",
        "persona_id": "software-engineer",
        "role": "generator"
      }
    ],
    "output_contract": {
      "type": "text",
      "description": "A concise implementation summary and validation result."
    }
  },
  "created_at": "2026-08-13T10:00:00Z",
  "created_by": "user-123",
  "updated_at": "2026-08-13T10:00:00Z",
  "updated_by": "user-123"
}
```

## Create an activity

`POST /api/v1/activities` creates an active Activity in the workspace supplied
by `X-Workspace-ID`. Every request needs a non-empty `name`, a `description`,
a supported `type`, and a configuration matching that type.

### Direct loop

Use a direct loop for an executable single-agent task. `max_iterations`,
`max_tokens`, and `timeout_seconds` are optional individually, but at least one
stop condition and exactly one `generator` agent are required. Direct loops do
not allow `reviewer` or `aggregator` agents.

```http
POST /api/v1/activities
X-Workspace-ID: workspace-acme
Content-Type: application/json
```

```json
{
  "name": "ImplementRequestedChange",
  "description": "Make and validate a focused code change.",
  "type": "direct_loop",
  "config": {
    "stop_conditions": {
      "max_iterations": 3,
      "max_tokens": 12000
    },
    "agents": [
      {
        "model_id": "gpt-5",
        "persona_id": "software-engineer",
        "role": "generator"
      }
    ],
    "output_contract": {
      "type": "text",
      "description": "A concise implementation summary and validation result."
    }
  }
}
```

Example response (`201 Created`):

```json
{
  "id": "activity-implementation",
  "workspace_id": "workspace-acme",
  "name": "ImplementRequestedChange",
  "description": "Make and validate a focused code change.",
  "status": "active",
  "type": "direct_loop",
  "config": {
    "stop_conditions": {
      "max_iterations": 3,
      "max_tokens": 12000
    },
    "agents": [
      {
        "model_id": "gpt-5",
        "persona_id": "software-engineer",
        "role": "generator"
      }
    ],
    "output_contract": {
      "type": "text",
      "description": "A concise implementation summary and validation result."
    }
  },
  "created_at": "2026-08-13T10:00:00Z",
  "created_by": "user-123",
  "updated_at": "2026-08-13T10:00:00Z",
  "updated_by": "user-123"
}
```

### Roundtable loop

Use a roundtable loop for an executable discussion between specialised agents.
It requires at least two `generator` agents and exactly one `aggregator` agent.
Roundtable loops do not allow `reviewer` agents.

```json
{
  "name": "ReviewReleasePlan",
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
      "type": "json",
      "description": "The release decision and its rationale.",
      "schema": {
        "type": "object",
        "required": ["decision", "rationale"],
        "properties": {
          "decision": {
            "type": "string"
          },
          "rationale": {
            "type": "string"
          }
        }
      }
    }
  }
}
```

Example response (`201 Created`):

```json
{
  "id": "activity-release-review",
  "workspace_id": "workspace-acme",
  "name": "ReviewReleasePlan",
  "description": "Reach a shared decision about release readiness.",
  "status": "active",
  "type": "roundtable_loop",
  "config": {
    "stop_conditions": {"max_iterations": 2},
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
      "type": "json",
      "description": "The release decision and its rationale.",
      "schema": {
        "type": "object",
        "required": ["decision", "rationale"],
        "properties": {
          "decision": {
            "type": "string"
          },
          "rationale": {
            "type": "string"
          }
        }
      }
    }
  },
  "created_at": "2026-08-13T10:00:00Z",
  "created_by": "user-123",
  "updated_at": "2026-08-13T10:00:00Z",
  "updated_by": "user-123"
}
```

### Refinement loop

Use a refinement loop for an iterative improvement task. It requires exactly
one `generator`, at least one `reviewer`, and no `aggregator`. After applying a
generated plan, reviewers approve the changed files or request a new iteration
within the configured `max_iterations` limit.

```json
{
  "name": "RefineDocumentationDraft",
  "description": "Improve a draft through review iterations.",
  "type": "refinement_loop",
  "config": {
    "stop_conditions": {
      "timeout_seconds": 900
    },
    "agents": [
      {
        "model_id": "gpt-5",
        "persona_id": "technical-writer",
        "role": "generator"
      },
      {
        "model_id": "gpt-5",
        "persona_id": "documentation-reviewer",
        "role": "reviewer"
      }
    ],
    "output_contract": {
      "type": "files",
      "description": "An updated API guide.",
      "files": ["doc/API.md"]
    }
  }
}
```

Example response (`201 Created`):

```json
{
  "id": "activity-documentation-refinement",
  "workspace_id": "workspace-acme",
  "name": "RefineDocumentationDraft",
  "description": "Improve a draft through review iterations.",
  "status": "active",
  "type": "refinement_loop",
  "config": {
    "stop_conditions": {"timeout_seconds": 900},
    "agents": [
      {
        "model_id": "gpt-5",
        "persona_id": "technical-writer",
        "role": "generator"
      },
      {
        "model_id": "gpt-5",
        "persona_id": "documentation-reviewer",
        "role": "reviewer"
      }
    ],
    "output_contract": {
      "type": "files",
      "description": "An updated API guide.",
      "files": ["doc/API.md"]
    }
  },
  "created_at": "2026-08-13T10:00:00Z",
  "created_by": "user-123",
  "updated_at": "2026-08-13T10:00:00Z",
  "updated_by": "user-123"
}
```

### Approval

Use an approval activity for a human decision. Its configuration has no
additional fields.

```json
{
  "name": "ApproveProductionRelease",
  "description": "A release manager must approve deployment to production.",
  "type": "approval",
  "config": {}
}
```

Example response (`201 Created`):

```json
{
  "id": "activity-production-approval",
  "workspace_id": "workspace-acme",
  "name": "ApproveProductionRelease",
  "description": "A release manager must approve deployment to production.",
  "status": "active",
  "type": "approval",
  "config": {},
  "created_at": "2026-08-13T10:00:00Z",
  "created_by": "user-123",
  "updated_at": "2026-08-13T10:00:00Z",
  "updated_by": "user-123"
}
```

### Quiz

Use a quiz activity to collect structured human answers. The `quiz` object is
application-defined and stored as supplied.

```json
{
  "name": "DeploymentReadinessQuiz",
  "description": "Confirm operational readiness before deployment.",
  "type": "quiz",
  "config": {
    "quiz": {
      "questions": [
        {
          "id": "rollback-tested",
          "prompt": "Has the rollback procedure been tested?",
          "required": true
        }
      ]
    }
  }
}
```

Example response (`201 Created`):

```json
{
  "id": "activity-deployment-quiz",
  "workspace_id": "workspace-acme",
  "name": "DeploymentReadinessQuiz",
  "description": "Confirm operational readiness before deployment.",
  "status": "active",
  "type": "quiz",
  "config": {
    "quiz": {
      "questions": [
        {
          "id": "rollback-tested",
          "prompt": "Has the rollback procedure been tested?",
          "required": true
        }
      ]
    }
  },
  "created_at": "2026-08-13T10:00:00Z",
  "created_by": "user-123",
  "updated_at": "2026-08-13T10:00:00Z",
  "updated_by": "user-123"
}
```

## Update an activity

`PATCH /api/v1/activities/{activity_id}` accepts one or more of `name`,
`description`, `status`, `config`, `model_target`, and `harness`. `status` must
be `active`, `disabled`, or `archived`. A replacement `config` must match the
persisted immutable Activity type and must not include `type`. Setting
`model_target` or `harness` to `null` clears that override.

```http
PATCH /api/v1/activities/activity-implementation
X-Workspace-ID: workspace-acme
Content-Type: application/json
```

```json
{
  "status": "disabled"
}
```

Example response (`200 OK`):

```json
{
  "id": "activity-implementation",
  "workspace_id": "workspace-acme",
  "name": "ImplementRequestedChange",
  "description": "Make and validate a focused code change.",
  "status": "disabled",
  "type": "direct_loop",
  "config": {
    "stop_conditions": {
      "max_iterations": 3,
      "max_tokens": 12000
    },
    "agents": [
      {
        "model_id": "gpt-5",
        "persona_id": "software-engineer",
        "role": "generator"
      }
    ],
    "output_contract": {
      "type": "text",
      "description": "A concise implementation summary and validation result."
    }
  },
  "created_at": "2026-08-13T10:00:00Z",
  "created_by": "user-123",
  "updated_at": "2026-08-13T10:15:00Z",
  "updated_by": "user-123"
}
```

## Delete an activity

`DELETE /api/v1/activities/{activity_id}` removes an Activity definition while
preserving its changelog entries.

```http
DELETE /api/v1/activities/activity-implementation
X-Workspace-ID: workspace-acme
```

Example response (`200 OK`):

```json
{
  "deleted": true
}
```

The endpoint returns `404 activity_not_found` when the Activity does not exist
in the selected workspace.

## Loop activity runs

Only active activities with `type: "direct_loop"`, `type: "refinement_loop"`,
or `type: "roundtable_loop"` can run. Their `config` is captured when a run is
created, so later definition changes do not alter an in-progress run.

| Method | Path | Purpose |
| ------ | ---- | ------- |
| `GET` | `/api/v1/activities/{activity_id}/runs` | List runs for a loop activity. |
| `GET` | `/api/v1/activities/{activity_id}/runs/{run_id}` | Describe a run. |
| `POST` | `/api/v1/activities/{activity_id}/runs/{run_id}/continue` | Submit one runtime or human checkpoint result. |

`GET /api/v1/activities/{activity_id}/runs` returns ten runs after the
optional non-negative `offset`.

```http
GET /api/v1/activities/activity-implementation/runs?offset=0
X-Workspace-ID: workspace-acme
```

Example response (`200 OK`):

```json
{
  "items": [
    {
      "id": "run-implementation-001",
      "activity_id": "activity-implementation",
      "input": "Implement the requested change.",
      "status": "in_progress",
      "state": "awaiting_snapshot",
      "next_action": "collect_snapshot",
      "iteration": 1,
      "token_revision": 1,
      "continuation_token": "continuation-token",
      "created_at": "2026-08-13T10:05:00Z",
      "created_by": "user-123",
      "updated_at": "2026-08-13T10:05:00Z",
      "payload": {}
    }
  ],
  "total": 1
}
```

## Describe an activity run

`GET /api/v1/activities/{activity_id}/runs/{run_id}` returns one complete run
owned by the selected Activity.

```http
GET /api/v1/activities/activity-implementation/runs/run-implementation-001
X-Workspace-ID: workspace-acme
```

Example response (`200 OK`):

```json
{
  "id": "run-implementation-001",
  "activity_id": "activity-implementation",
  "input": "Implement the requested change.",
  "status": "in_progress",
  "state": "awaiting_snapshot",
  "next_action": "collect_snapshot",
  "iteration": 1,
  "token_revision": 1,
  "continuation_token": "continuation-token",
  "created_at": "2026-08-13T10:05:00Z",
  "created_by": "user-123",
  "updated_at": "2026-08-13T10:05:00Z",
  "payload": {}
}
```

Run creation accepts the existing request body:

```json
{
  "input": "Implement the requested change."
}
```

Example response (`201 Created`):

```json
{
  "id": "run-implementation-001",
  "activity_id": "activity-implementation",
  "input": "Implement the requested change.",
  "status": "in_progress",
  "state": "awaiting_snapshot",
  "next_action": "collect_snapshot",
  "iteration": 1,
  "token_revision": 1,
  "continuation_token": "continuation-token",
  "created_at": "2026-08-13T10:05:00Z",
  "created_by": "user-123",
  "updated_at": "2026-08-13T10:05:00Z",
  "payload": {}
}
```

## Continue an activity run

`POST /api/v1/activities/{activity_id}/runs/{run_id}/continue` submits one
idempotent CLI checkpoint result. Every request requires the current
`continuation_token`, a unique `idempotency_key`, and a result object whose
`action` matches the run's `next_action`.

```http
POST /api/v1/activities/activity-implementation/runs/run-implementation-001/continue
X-Workspace-ID: workspace-acme
Content-Type: application/json
```

```json
{
  "continuation_token": "continuation-token",
  "idempotency_key": "checkpoint-001",
  "result": {
    "action": "collect_snapshot",
    "repo_context": "Repository context for generation.",
    "workspace_metadata": {
      "workspace_path": "/workspace/project",
      "source_commit_sha": "a1b2c3d4"
    },
    "constitution": "Repository contribution rules.",
    "project_profile": {
      "source_file_count": 24,
      "approximate_source_chars": 12000,
      "extension_counts": {
        ".py": 24
      },
      "top_level_entries": ["src", "tests"],
      "markers": {
        "nuxt": false,
        "package_json": false,
        "fastapi": true,
        "docker": false,
        "tests": true
      }
    }
  }
}
```

The endpoint returns the updated Activity run (`200 OK`). A run selected by a
Pipeline additionally requires its `pipeline_run_id` and active Pipeline
`lease_token`. The API rejects a missing, expired, or mismatched lease with
`409 activity_run_invalid_transition` before persisting a checkpoint result.

Requests for inactive or non-executable activities return
`409 activity_run_unavailable`. An invalid or stale continuation token returns
`409 activity_run_token_conflict`.

Standalone Activity runs continue with their checkpoint token and idempotency
key. A child run selected by a Pipeline additionally requires its
`pipeline_run_id` and active Pipeline `lease_token`. The API rejects a missing,
expired, or mismatched lease with `409 activity_run_invalid_transition` before it
persists the checkpoint result.

## List activity changelog entries

`GET /api/v1/activities/{activity_id}/changelog` returns ten newest entries
after the optional non-negative `offset`.

```http
GET /api/v1/activities/activity-implementation/changelog?offset=0
X-Workspace-ID: workspace-acme
```

Example response (`200 OK`):

```json
{
  "items": [
    {
      "id": "activity-change-002",
      "activity_id": "activity-implementation",
      "change_type": "disabled",
      "actor_id": "user-123",
      "changed_at": "2026-08-13T10:15:00Z",
      "diff": {
        "status": {
          "from": "active",
          "to": "disabled"
        }
      },
      "content": null
    }
  ],
  "total": 2
}
```
