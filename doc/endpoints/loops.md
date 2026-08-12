# Retired Loop Endpoints

Loop endpoints are retired. Use [Activities](activities.md) for loop
definitions and loop-activity runs.

<!--

A loop stores a validated flow, its model/persona agents, stop conditions, and
the expected output. The API stores this definition but does not execute it.

## Loop calls

| Method | Path | Description |
| ------ | ---- | ----------- |
| `GET` | `/api/v1/loops` | Lists up to ten complete loop definitions. |
| `POST` | `/api/v1/loops` | Creates an active loop. |
| `GET` | `/api/v1/loops/{loop_id}` | Returns one complete loop. |
| `PATCH` | `/api/v1/loops/{loop_id}` | Updates supplied mutable fields or changes status. |
| `DELETE` | `/api/v1/loops/{loop_id}` | Permanently deletes a loop while retaining its changelog. |
| `GET` | `/api/v1/loops/{loop_id}/changelog` | Lists up to ten newest immutable changelog entries. |

## Create Loop Request

| Field | Description |
| ----- | ----------- |
| `title` | Required non-empty display title. |
| `description` | Required description. |
| `flow` | `direct`, `refinement`, or `roundtable`. |
| `stop_conditions` | At least one positive supported stop condition. |
| `agents` | Flow-compatible model, persona, and role assignments. |
| `output_contract` | Generic `text`, `json`, or `files` output description. |

Agents require `model_id`, `persona_id`, and a `generator`, `reviewer`, or
`aggregator` role. Their `id` is optional and generated when omitted. Agents do
not accept skills. `direct` requires at least one agent and at most one
aggregator. `refinement` requires exactly one generator and at least one
reviewer. `roundtable` requires at least two generators and exactly one
aggregator.

`stop_conditions` supports optional positive `max_iterations`, `max_tokens`,
and `timeout_seconds` values, with at least one configured. A `files` output
requires at least one path; a `json` output requires a JSON object in `schema`.

## Create Loop Example

```sh
curl -s -X POST http://127.0.0.1:8000/api/v1/loops \
  -H "Content-Type: application/json" \
  -H "X-Workspace-ID: workspace-id" \
  -d '{
    "title": "Implementation loop",
    "description": "One generator with an independent reviewer.",
    "flow": "refinement",
    "stop_conditions": {
      "max_iterations": 3,
      "max_tokens": 50000
    },
    "agents": [
      {
        "model_id": "gpt-5.6-terra",
        "persona_id": "builtin:persona:tech_lead",
        "role": "generator"
      },
      {
        "model_id": "kimi-k2.6",
        "persona_id": "builtin:persona:devils_advocate",
        "role": "reviewer"
      }
    ],
    "output_contract": {
      "type": "files",
      "description": "Produce the implementation plan.",
      "files": ["plan.md"]
    }
  }'
```

The API generates the loop ID, missing agent IDs, `active` status, timestamps,
and actor fields. PATCH replaces the complete agent array when supplied,
preserves omitted fields, and rejects empty or ineffective changes. An archived
loop is immutable except for a status-only reactivation to `active`.

Every create, update, status transition, and delete writes an immutable
changelog entry in the same transaction. Creation and deletion entries contain
the complete loop representation; update entries contain only changed fields.
The changelog remains available after deletion.

Every workspace initially receives two ordinary, active catalog loops:
`shape ideas`, which produces `ideas.md`, and `plan implementation`, which
produces `tasks.json`. All their agents use `deepseek-v4-pro`. Installation is
performed only once per workspace, so either loop can subsequently be modified
or deleted without being reset or recreated.

## Loop run calls

Loop runs are persisted checkpoints for executing a loop with a CLI-owned
repository. The API creates and advances the run; the CLI supplies repository
snapshots, applies planned file operations, submits review input, and attempts
commits. The API does not expose standalone run routes: every run is addressed
through its parent loop.

| Method | Path | Description |
| ------ | ---- | ----------- |
| `GET` | `/api/v1/loops/{loop_id}/runs` | Lists ten newest runs after an optional offset. |
| `POST` | `/api/v1/loops/{loop_id}/runs` | Creates a run awaiting its first snapshot. |
| `GET` | `/api/v1/loops/{loop_id}/runs/{run_id}` | Returns one persisted run. |
| `POST` | `/api/v1/loops/{loop_id}/runs/{run_id}/continue` | Advances one idempotent execution checkpoint. |

Create a run with a non-empty `input`:

```json
{
  "input": "Implement the requested change."
}
```

The response includes the run `status`, current `state`, `next_action`,
iteration, continuation token, timestamps, and a `payload` containing exposed
runtime artifacts. A newly created run is `in_progress`, awaits a repository
snapshot, and does not begin model generation until the CLI continues it.

Each continuation request must include the current non-empty
`continuation_token`, a non-empty `idempotency_key`, and a result whose
`action` is one of:

- `collect_snapshot`, which supplies repository context, workspace metadata,
  constitution, and project profile before generation;
- `apply_operations`, which reports whether API-planned file operations were
  applied and includes the resulting diff or error;
- `submit_review_input`, which supplies the final diff and changed file
  contents;
- `commit_if_allowed`, which reports whether the CLI committed and, when
  successful, supplies the commit SHA and message.

Continuation requests are safe to retry with the same idempotency key. The
server validates the action-specific result and rejects stale continuation
tokens or an action that is not valid for the run's current checkpoint.
-->
