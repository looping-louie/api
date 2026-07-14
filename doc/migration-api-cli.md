# API-CLI Migration Plan

This document defines the migration from the current single-repo execution
model into a split architecture with two repositories.

- looping-louie-api: LLM and orchestration decision engine.
- looping-louie-cli: local execution engine against user repositories.

The migration preserves backward compatibility until the CLI path is fully
operational.

---

## Current Intent

The target architecture separates decision-making from local execution:

- API decides what to do next.
- CLI executes filesystem, Git and workspace operations.
- API and CLI run on different servers.

The current API remains fully operational during migration.

---

## Agreed Constraints

- Keep API behavior backward-compatible until CLI is ready.
- Keep API-CLI calls synchronous.
- Keep traces in both systems with different scopes.
- Keep all `.looping-louie` artifacts in CLI.
- Start by trusting CLI execution reports.
- Defer authentication and authorization design.
- Keep code operational in API now so selected modules can later move to CLI.

## Naming Convention During Migration

Use schema names consistently to preserve clear boundaries:

- `*Request` and `*Response`: reserved for HTTP API contract models.
- `*Result`: reserved for internal service and method return models.

Example applied now:

- Harness service uses `RunHarnessRequest` + `RunHarnessResult`.
- API endpoints keep `RunTaskRequest`/`RunTaskResponse`,
  `RunWorkflowRequest`/`RunWorkflowResponse`, and
  `RunMeetingRequest`/`RunMeetingResponse`.

---

## Ten-Point Implication Analysis

### 1. Interaction Model Mismatch

The current API assumes direct repository access. The target split forbids API
filesystem access. CLI must provide execution state in request payloads.

### 2. State Authority and Replayability

Current run artifacts are produced by API-side local execution. In the target
split, CLI owns local execution artifacts. Correlation keys are required to
replay full runs end to end.

### 3. Instruction Granularity

Low-level instructions create brittle contracts. High-level instructions force
CLI duplication. A typed step protocol is required as the stable middle layer.

### 4. Idempotency and Retry Safety

Synchronous network retries can duplicate execution. Step IDs and idempotency
keys are required to prevent duplicate commits or repeated local actions.

### 5. Trust Model Side Effects

Trusting CLI is acceptable for phase one. API still needs schema and basic
consistency validation for reported results.

### 6. Harness Boundary Ambiguity

Current harness mixes decision logic and execution logic. Migration requires an
explicit split so decision modules remain in API and execution modules can move
into CLI.

### 7. Data Volume and Latency

Sending full snapshots every iteration can become expensive. The protocol needs
payload size limits and a path to hash-based references.

### 8. Backward Compatibility Pressure

Dual mode is required during migration:

- local execution mode for current users;
- remote instruction mode for CLI-based execution.

### 9. Commit Ownership Semantics

API decides whether to commit. CLI executes the commit. Commit intent must be
an explicit contract with preconditions and message.

### 10. Observability Split

API and CLI collect different metrics. Shared correlation fields are required to
join traces and debug complete runs.

---

## Responsibility Matrix

- LLM calls: API owns, CLI does not perform.
- Prompt composition: API owns, CLI does not perform.
- Planning and review decisions: API owns, CLI does not perform.
- Filesystem operations: CLI owns, API does not execute.
- Git operations: CLI owns, API does not execute.
- Workspace lifecycle: CLI owns, API does not execute.
- Local `.looping-louie` artifacts: CLI owns and persists.
- Action instruction generation: API owns and returns typed actions.
- Execution result reporting: CLI owns production, API owns consumption.

---

## Step Protocol V1

Each synchronous exchange uses these envelope fields:

- `run_id`: stable end-to-end run identifier.
- `iteration`: 1-based loop index.
- `step_id`: deterministic unique step identifier.
- `idempotency_key`: key for retry-safe execution.
- `mode`: `local` or `remote`.

Suggested step categories:

- `plan_iteration`
- `generate_patch`
- `apply_operations`
- `compute_diff`
- `run_reviewers`
- `finalize_run`
- `commit_task`

API responses in remote mode include:

- `next_action`: typed command for CLI.
- `required_inputs`: exact data expected in next request.
- `stop_condition`: whether the run is complete.

CLI responses include:

- `action_result`: success or failure.
- `artifacts`: structured outputs needed by API.
- `execution_metrics`: local execution timings and counters.

---

## Trace Split

API trace stores:

- prompts and model outputs;
- planner and reviewer decisions;
- API-side timing and token metrics.

CLI trace stores:

- workspace creation and cleanup events;
- filesystem and Git operation logs;
- local artifacts currently under `.looping-louie`.

Shared trace fields:

- `run_id`
- `iteration`
- `step_id`
- `idempotency_key`

---

## Migration Phases and Rollback Points

### Phase 0: Contracts and Documentation

- Define protocol and responsibility boundaries.
- Keep behavior unchanged.
- Rollback: remove contract-only files.

### Phase 1: Internal Decoupling in API

- Split orchestration from execution dependencies using ports.
- Keep local adapters as default path.
- Rollback: restore direct service calls.

### Phase 2: Dual Runtime Modes

- Add `local` and `remote` execution strategies.
- Keep local mode as default.
- Rollback: disable remote mode flag.

### Phase 3: CLI Remote Executor

- Implement action consumption in CLI.
- Report structured results back to API.
- Rollback: route users to local mode only.

### Phase 4: Gradual Ownership Transfer

- Move execution modules from API to CLI repository.
- Keep API interfaces stable.
- Rollback: restore moved modules in API and keep protocol unchanged.

### Phase 5: API Execution Cleanup

- Remove obsolete local execution modules from API.
- Keep decision and LLM orchestration in API.
- Rollback: re-enable local strategy from tagged fallback release.

---

## Immediate Next Engineering Step

Introduce a typed instruction schema in API responses while preserving current
response fields. This enables remote execution mode incrementally without
breaking existing local behavior.
