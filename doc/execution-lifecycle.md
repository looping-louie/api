# Execution lifecycle

A persisted Activity run coordinates API-owned decisions with a Harness that
executes repository work in a runtime-owned checkout. The API plans and
reviews changes; the `louie` Harness collects repository context, applies
operations, and performs the authorized commit. The `codex_cli` and
`copilot_cli` Harnesses run local agent turns and report their results for the
same API-owned review and commit decisions.

## Harness Selection

PipelineRun creation resolves Harnesses from Activity, Pipeline,
then User scope. It freezes the Pipeline-level effective Harness and each child
Activity-run's effective Harness independently. Existing configurations use
`louie` v1 when no Harness candidate exists.

A Harness has a stable `kind`, a `version`, and a kind-specific `config`
object. The API accepts `louie` v1, `codex_cli` v1, and `copilot_cli` v1, each
with an empty `config`.
Workers retain ownership of local checkout paths, executable locations,
credentials, and other machine configuration. Workers advertise Harness
capabilities at registration, and an active Worker claims a PipelineRun only
when it advertises an exact match for the frozen selection.

Human Activities do not use the Pipeline Harness. `approval` and `quiz`
Activities use the built-in `human` execution mode and accept only human
decision checkpoints.

The following Harness kinds define the current compatibility model:

| Harness kind | Supported Activity types | Execution behavior |
| ------------ | ------------------------ | ------------------ |
| `louie` | `direct_loop`, `refinement_loop`, `roundtable_loop` | Implemented: API generates operation plans; the Harness applies them locally. |
| `codex_cli` | `direct_loop`, `refinement_loop`, `roundtable_loop` | Runs one API-selected local CLI agent turn with the frozen model, then reports normalized results and a commit proposal through `run_harness`. |
| `copilot_cli` | `direct_loop`, `refinement_loop`, `roundtable_loop` | Runs one API-selected local CLI agent turn with the frozen model, then reports normalized results and a commit proposal through `run_harness`. |

## Activity-run lifecycle

### 1. Create and freeze a run

The API persists the activity snapshot, frozen Harness selection, run status,
checkpoint action, iteration, and continuation revision in SQLite.

For each CLI Harness agent, PipelineRun creation freezes its effective model as
`requested_model` and resolves its Persona and ordered Skills from the
User-owned instruction library. Their IDs, versions, metadata, and content are
persisted as a versioned `instruction_snapshot` inside the immutable Activity
snapshot. Each `run_harness` checkpoint returns the scheduled agent's exact
model and instruction snapshot; neither the API nor the runtime resolves the
mutable resources again. CLI authentication and executables remain local worker
concerns; API Linked Services are not used.

### 2. Receive context and select the next action

The runtime sends repository snapshot context in `collect_snapshot`. The API uses
that context and the frozen Activity snapshot to select the next checkpoint.

### 3. Advance the selected execution path

For the API-directed `louie` Harness, the API builds generator and reviewer
prompts, calls the configured model through its selected Linked Service, and
validates the resulting filesystem operation plan. It returns that plan through
the `apply_operations` checkpoint. After local application, the runtime submits
review input when the Activity has reviewers.

For `codex_cli` and `copilot_cli`, the API schedules one `run_harness` turn for
the selected writer, proposal, review, or aggregation role. It validates the
reported frozen Harness and requested model, retains the normalized observation,
and schedules the next turn or finalizes the loop. The runtime constructs the
local CLI prompt from the API-supplied turn and immutable instructions.

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
The runtime remains responsible for applying local Git policy and reporting the
commit outcome.

## Workspace and workflow ownership

Workspace lifecycle is runtime-owned. The API persists activity-run
orchestration state in SQLite.

The API queues a persisted Pipeline run. A Worker claims it, then the frozen
selected Harness executes each requested checkpoint and reports Activity
outcomes through `/continue` so the API can select the next step. For
commit-enabled work, the runtime commits only after API authorization.

Harnesses report normalized execution observations. A report can include a
final message, diff, changed files, duration, usage, bounded diagnostics, and
an optional opaque session reference. The API retains ownership of durable
state transitions, review decisions, retries, and commit authorization.

## Persisted execution data

Successful and failed CLI Harness results persist a normalized observation in
the ActivityRun `payload`. The v1 envelope identifies its `schema_version` and
frozen `harness`, followed by timestamps, duration, model observations, usage,
process outcome, Git state, response, diagnostics, and failure detail. CLI
Harness variants add materialized Skill versions; `codex_cli` v1 also reports
observed reasoning effort. Partial observations from a failed process remain
available for inspection. A successful `commit_if_allowed` updates the final
Git SHA with the authorized commit SHA.
