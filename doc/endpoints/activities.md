# Activities

Activities are workspace-scoped reusable units of work. The current supported
types are `approval`, `quiz`, `direct_loop`, `refinement_loop`, and
`roundtable_loop`. Approval activities represent human approval, and quiz
activities collect human quiz responses. Direct and roundtable loop activities
can create persisted runs; refinement, approval, and quiz execution are
reserved for future pipeline orchestration.

## Resource endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/v1/activities` | List activities. |
| `POST` | `/api/v1/activities` | Create an activity. |
| `GET` | `/api/v1/activities/{activity_id}` | Get an activity. |
| `PATCH` | `/api/v1/activities/{activity_id}` | Update an activity. |
| `DELETE` | `/api/v1/activities/{activity_id}` | Delete an activity. |
| `GET` | `/api/v1/activities/{activity_id}/changelog` | List activity history. |

Activity creation specifies a common `type` and a matching discriminated
`config.type`. The activity type is immutable after creation.

## Create an activity

`POST /api/v1/activities` creates an active Activity in the workspace supplied
by `X-Workspace-ID`. Every request needs a non-empty `title`, a `description`,
and matching `type` and `config.type` values.

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
  "title": "Implement requested change",
  "description": "Make and validate a focused code change.",
  "type": "direct_loop",
  "config": {
    "type": "direct_loop",
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

### Roundtable loop

Use a roundtable loop for an executable discussion between specialised agents.
Agents can use the `generator`, `reviewer`, and `aggregator` roles.

```json
{
  "title": "Review release plan",
  "description": "Reach a shared decision about release readiness.",
  "type": "roundtable_loop",
  "config": {
    "type": "roundtable_loop",
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
          "decision": {"type": "string"},
          "rationale": {"type": "string"}
        }
      }
    }
  }
}
```

### Refinement loop

Use a refinement loop to store a multi-pass improvement definition. It has the
same configuration shape as executable loop types, but cannot currently create
runs.

```json
{
  "title": "Refine documentation draft",
  "description": "Improve a draft through review iterations.",
  "type": "refinement_loop",
  "config": {
    "type": "refinement_loop",
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

### Approval

Use an approval activity for a human decision. Its configuration has no
additional fields.

```json
{
  "title": "Approve production release",
  "description": "A release manager must approve deployment to production.",
  "type": "approval",
  "config": {
    "type": "approval"
  }
}
```

### Quiz

Use a quiz activity to collect structured human answers. The `quiz` object is
application-defined and stored as supplied.

```json
{
  "title": "Deployment readiness quiz",
  "description": "Confirm operational readiness before deployment.",
  "type": "quiz",
  "config": {
    "type": "quiz",
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

## Loop activity runs

Only active activities with `type: "direct_loop"` or
`type: "roundtable_loop"` can run. Their `config` is captured when a run is
created, so later definition changes do not alter an in-progress run.

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/v1/activities/{activity_id}/runs` | List runs for a loop activity. |
| `POST` | `/api/v1/activities/{activity_id}/runs` | Create a run. |
| `GET` | `/api/v1/activities/{activity_id}/runs/{run_id}` | Get one run. |
| `POST` | `/api/v1/activities/{activity_id}/runs/{run_id}/continue` | Submit one CLI checkpoint result. |

Run creation accepts the existing request body:

```json
{
  "input": "Implement the requested change."
}
```

Checkpoint responses and continuation payloads are identical to the legacy
loop-run protocol. Requests for inactive or non-loop activities return
`409 activity_run_unavailable`.
