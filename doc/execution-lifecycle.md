# Execution lifecycle

This document is the API authority for execution state, frozen configuration,
Harness selection, and checkpoint transitions. Runtime-local checkout and CLI
behavior is owned by the runtime documentation.

## Harness Selection

PipelineRun creation resolves Harnesses from Activity, Pipeline,
then User scope. It freezes the Pipeline-level effective Harness and each child
Activity-run's effective Harness independently. Existing configurations use
`louie` v1 when no Harness candidate exists.

A Harness has a stable `kind`, a `version`, and a kind-specific `config`
object. The API accepts `louie` v1, `codex_cli` v1, and `copilot_cli` v1, each
with an empty `config`. It permits a Worker to claim a PipelineRun only when the
Worker advertises an exact match for the frozen selection.

Human Activities do not use the Pipeline Harness. `approval` and `quiz`
Activities use the built-in `human` execution mode and accept only human
decision checkpoints.

The following Harness kinds define the current compatibility model:

| Harness kind | Supported Activity types | Execution behavior |
| ------------ | ------------------------ | ------------------ |
| `louie` | `direct_loop`, `refinement_loop`, `roundtable_loop` | API creates and validates operation plans. |
| `codex_cli` | `direct_loop`, `refinement_loop`, `roundtable_loop` | API schedules normalized `run_harness` turns. |
| `copilot_cli` | `direct_loop`, `refinement_loop`, `roundtable_loop` | API schedules normalized `run_harness` turns. |

## Activity-run lifecycle

### 1. Create and freeze a run

The API persists the activity snapshot, frozen Harness selection, run status,
checkpoint action, iteration, and continuation revision in SQLite.

For each CLI Harness agent, PipelineRun creation freezes its effective model as
`requested_model` and resolves its Persona and ordered Skills from the
User-owned instruction library. Their IDs, versions, metadata, and content are
persisted as a versioned `instruction_snapshot` inside the immutable Activity
snapshot. Each `run_harness` checkpoint exposes the scheduled agent's exact
model and instruction snapshot. API Linked Services are not used for CLI
Harness turns.

### 2. Receive a checkpoint and select the next action

The API validates each continuation token, idempotency key, Pipeline lease, and
checkpoint result before changing durable state. `collect_snapshot` supplies
repository context used with the frozen Activity snapshot to select the next
checkpoint.

### 3. Advance the selected execution path

For the API-directed `louie` Harness, the API builds generator and reviewer
prompts, calls the configured model through its selected Linked Service, and
validates the resulting filesystem operation plan. It returns the plan through
`apply_operations` and schedules `submit_review_input` when the Activity has
reviewers.

For `codex_cli` and `copilot_cli`, the API schedules one `run_harness` turn for
the selected writer, proposal, review, or aggregation role. It validates the
reported frozen Harness and requested model, retains the normalized observation,
and schedules the next turn or finalizes the loop.

Human `approval` and `quiz` Activities enter the built-in `human` execution
mode. A user decision advances the Activity without a runtime Harness.

### 4. Review and advance the run

The API applies the configured loop semantics to reported work. It records
review outcomes, schedules a retry when applicable, advances the Pipeline after
a terminal Activity outcome, or makes the Pipeline run terminal.

### 5. Authorize and record completion

For commit-enabled work, the API authorizes commit handoff only after a
successful Activity result. A CLI Harness must provide a non-empty
`commit_message`; the API persists it and returns it only in the later
`commit_if_allowed` checkpoint. A `forbid` run does not enter that checkpoint.

## Persisted execution data

Successful and failed CLI Harness results persist a normalized observation in
the ActivityRun `payload`. The v1 envelope identifies its `schema_version` and
frozen `harness`, followed by timestamps, duration, model observations, usage,
process outcome, Git state, response, diagnostics, and failure detail. CLI
Harness variants add materialized Skill versions; `codex_cli` v1 also reports
observed reasoning effort. Partial observations from a failed process remain
available for inspection. A successful `commit_if_allowed` updates the final
Git SHA with the authorized commit SHA.
