# Activities

Activities are workspace-scoped, possibly reusable units of work. They can be
created directly or generated when an inline definition is supplied while
creating or updating a Pipeline. The current supported types are `approval`,
`quiz`, `direct_loop`, `refinement_loop`, and `roundtable_loop`. Approval
activities represent human approval, and quiz activities collect human quiz
responses. Direct and roundtable loop activities can create persisted runs;
refinement, approval, and quiz execution are reserved for future pipeline
orchestration.

## Resource endpoints

| Method | Path | Purpose |
| --- | --- | --- |
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

## Activity runs

Direct and roundtable loop activities expose persisted executions at
`/api/v1/activities/{activity_id}/runs`. Each run response identifies its
owning definition with `activity_id`; it does not expose a legacy loop
identifier.

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
stop condition is required.

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
Agents can use the `generator`, `reviewer`, and `aggregator` roles.

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
        "persona_id": "quality-reviewer",
        "role": "reviewer"
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
        "persona_id": "quality-reviewer",
        "role": "reviewer"
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

Use a refinement loop to store a multi-pass improvement definition. It has the
same configuration shape as executable loop types, but cannot currently create
runs.

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
`description`, `status`, and `config`. `status` must be `active`, `disabled`,
or `archived`. A replacement `config` must match the persisted immutable
Activity type and must not include `type`.

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

## Loop activity runs

Only active activities with `type: "direct_loop"` or
`type: "roundtable_loop"` can run. Their `config` is captured when a run is
created, so later definition changes do not alter an in-progress run.

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/v1/activities/{activity_id}/runs` | List runs for a loop activity. |
| `POST` | `/api/v1/activities/{activity_id}/runs` | Create a run. |
| `GET` | `/api/v1/activities/{activity_id}/runs/{run_id}` | Describe a run. |
| `POST` | `/api/v1/activities/{activity_id}/runs/{run_id}/continue` | Submit one CLI checkpoint result. |

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
      "loop_id": "activity-implementation",
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
  "loop_id": "activity-implementation",
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
  "loop_id": "activity-implementation",
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

Checkpoint responses and continuation payloads are identical to the legacy
loop-run protocol. Requests for inactive or non-loop activities return
`409 activity_run_unavailable`.

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
