# Task Checkpoint Protocol V1

## Purpose

This document defines a synchronous checkpoint protocol that replaced the former
monolithic `POST /task/run` flow with resumable API-CLI exchanges.

The protocol keeps API as the decision engine and moves local execution to CLI.

## Why This Exists

The legacy single-call flow combined three responsibilities in one API request:

- build iteration prompt and call generator model;
- apply generator operations to workspace and compute local diff;
- run reviewers and decide whether to continue.

Local repository mutations belong to CLI in the target
architecture. A checkpoint protocol lets API and CLI alternate responsibilities
at every iteration without losing run continuity.

## Scope

This protocol is the canonical task execution contract.

Workflow execution in CLI reuses this task envelope by executing each workflow
task through `POST /task/start` and `POST /task/continue`.

## Core Ideas

- API owns run state, planning, reviewer decisions, and model calls.
- CLI owns workspace lifecycle, filesystem operations, Git diff generation, and
  local artifact persistence.
- Every exchange returns an opaque `continuation_token`.
- CLI sends an `idempotency_key` on each continuation call.
- API advances exactly one state transition per call.

## Run Envelope

Every response and continuation request includes these fields:

- `run_id`: stable identifier for one task run.
- `iteration`: 1-based current iteration.
- `status`: `in_progress`, `completed`, `stopped`, `failed`, or `expired`.
- `next_action`: required CLI action when `status=in_progress`.
- `continuation_token`: opaque API token for next call.
- `token_revision`: monotonic integer managed by API.

## Next Actions

- `collect_snapshot`: CLI builds repository snapshot from local repo state and sends it.
- `apply_operations`: CLI applies API-provided operations locally.
- `submit_review_input`: CLI sends final diff and changed file contents.
- `commit_if_allowed`: CLI commits approved changes locally.
- `none`: terminal state.

## Endpoints

### 1) Start Run

`POST /task/start`

Request fields:

- `repo_path`
- `task`
- `constitution`
- `project_profile`
- planner/reviewer/generator model settings

Response:

- creates run state;
- computes execution plan;
- returns first checkpoint with `next_action=collect_snapshot`.

### 2) Continue Run

`POST /task/continue`

Request fields:

- `run_id`
- `continuation_token`
- `idempotency_key`
- `action`
- `action_result` (schema depends on `action`)

Response:

- validates token and idempotency;
- executes one transition;
- returns next checkpoint.

### 3) Get Run (Optional but Recommended)

`GET /task/{run_id}`

Response:

- returns latest checkpoint and terminal result if available;
- supports crash recovery and operator debugging.

### 4) Cancel Run (Optional)

`POST /task/{run_id}/cancel`

Response:

- moves run to terminal `stopped` state.

## Action Result Schemas

### collect_snapshot -> action_result

- `repo_context`: formatted snapshot text from local repository state.
- `workspace_metadata`:
    - `workspace_path`
    - `source_commit_sha`

API transition:

- builds generator prompt using latest reviewer feedback;
- calls generator model;
- parses/validates generator output into operations;
- returns `next_action=apply_operations` with operation payload.

### apply_operations -> action_result

- `applied`: boolean.
- `error`: optional string.
- `final_diff`: optional string.
- `changed_files`: optional array of paths.

API transition:

- if `applied=false`, records system failure for this iteration and returns
  next checkpoint as `submit_review_input` with synthetic failure context;
- if `applied=true`, returns `next_action=submit_review_input`.

### submit_review_input -> action_result

- `final_diff`
- `changed_file_contents`: map path -> content

API transition:

- runs reviewers;
- aggregates metrics;
- if approved: returns terminal `completed` and `next_action=commit_if_allowed`;
- if not approved and iterations remain: increments iteration and returns
  `next_action=collect_snapshot`;
- if not approved and limit reached: returns terminal `stopped`.

### commit_if_allowed -> action_result

- `committed`: boolean
- `commit_sha`: optional string
- `commit_message`: optional string
- `error`: optional string

API transition:

- finalizes run result with commit metadata;
- terminal `completed`.

## Example Checkpoint Response

```json
{
  "run_id": "f0a1b2c3d4e5",
  "iteration": 2,
  "status": "in_progress",
  "next_action": "apply_operations",
  "continuation_token": "eyJ2IjoxMSwiZXhwIjoxNzI...",
  "token_revision": 11,
  "payload": {
    "operations": [
      {
        "operation": "replace_text",
        "path": "src/app/service.py",
        "old_content": "foo",
        "new_content": "bar"
      }
    ],
    "generator_metrics": {
      "model": "deepseek-ai/DeepSeek-V4-Pro",
      "input_tokens": 1234,
      "output_tokens": 456,
      "duration_ms": 4200
    }
  }
}
```

## API State Machine (Minimal)

- `created`
- `awaiting_snapshot`
- `awaiting_apply_result`
- `awaiting_review_input`
- `awaiting_commit_result`
- `completed`
- `stopped`
- `failed`
- `expired`

Valid transitions:

- `created -> awaiting_snapshot`
- `awaiting_snapshot -> awaiting_apply_result`
- `awaiting_apply_result -> awaiting_review_input`
- `awaiting_review_input -> awaiting_snapshot` (not approved, retry)
- `awaiting_review_input -> awaiting_commit_result` (approved)
- `awaiting_review_input -> stopped` (max iterations)
- `awaiting_commit_result -> completed`
- any non-terminal -> `failed` or `expired`

## Idempotency and Ordering Rules

- API keys idempotency by `(run_id, token_revision, idempotency_key)`.
- Repeated continuation with same tuple returns same response body.
- API rejects stale tokens with `409 token_conflict`.
- API rejects unexpected action for current state with `409 invalid_transition`.

## Expiration and Recovery

- `continuation_token` includes expiration.
- Expired token returns `410 token_expired` with latest run state.
- CLI can recover by calling `GET /task/{run_id}`.

## Error Model

Use explicit, typed errors:

- `token_conflict`
- `token_expired`
- `invalid_transition`
- `invalid_action_result`
- `run_not_found`
- `run_cancelled`

Every error includes:

- `run_id`
- `token_revision`
- `message`
- `recoverable`: boolean

## How This Helps The Migration

- CLI can own workspace and local mutations immediately.
- API keeps planner/reviewer/model logic with minimal rewrite.
- Existing loop semantics remain intact, but are externalized into checkpoints.
- Workflow can reuse this protocol with a parent workflow envelope.

## Implementation Status

1. `POST /task/start` and `POST /task/continue` are the canonical task
  execution path.
2. API run-state persistence for checkpoint fields is active.
3. CLI `task run` uses checkpoint continuation as the default execution path.
4. CLI `workflow run` reuses the same checkpoint task execution loop.
5. Legacy monolithic task execution endpoint is removed.

## Non-Goals for V1

- Streaming responses.
- Asynchronous queue workers.
- Multi-client concurrent continuation on one run.
- Zero-copy artifact transfer optimization.
