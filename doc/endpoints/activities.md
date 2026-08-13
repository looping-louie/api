# Activities

Activities are workspace-scoped reusable units of work. The current supported
types are `approval`, `quiz`, `direct_loop`, and `loop`. Approval activities
represent human approval, and quiz activities collect human quiz responses.
Direct-loop activities can create persisted runs; approval and quiz execution
are reserved for future pipeline orchestration.

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

## Loop activity runs

Only active activities with `type: "direct_loop"` can run. Their `config` is
captured when a run is created, so later definition changes do not alter an
in-progress run.

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
