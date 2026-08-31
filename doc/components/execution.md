# Execution

A persisted Activity run coordinates API-owned decisions with a Harness that
executes repository work in a runtime-owned checkout. The API plans and
reviews changes; the `louie` Harness collects repository context, applies
operations, and performs the authorized commit. The `codex_cli` Harness runs
one local direct-loop turn and reports its result for the same API-owned review
and commit decisions.

## Harness Selection

PipelineRun creation resolves Harnesses from Activity, Pipeline,
then User scope. It freezes the Pipeline-level effective Harness and each child
Activity-run's effective Harness independently. Existing configurations use
`louie` v1 when no Harness candidate exists.

A Harness has a stable `kind`, a `version`, and a kind-specific `config`
object. The API accepts `louie` v1 and `codex_cli` v1, each with an empty
`config`.
Workers retain ownership of local checkout paths, executable locations,
credentials, and other machine configuration. Workers advertise Harness
capabilities at registration, and an active Worker claims a PipelineRun only
when it advertises an exact match for the frozen selection.

Human Activities do not use the Pipeline Harness. `approval` and `quiz`
Activities use the built-in `human` execution mode and accept only human
decision checkpoints.

The following Harness kinds define the initial compatibility model:

| Harness kind | Supported Activity types | Execution behavior |
| ------------ | ------------------------ | ------------------ |
| `louie` | `direct_loop`, `refinement_loop`, `roundtable_loop` | Implemented: API generates operation plans; the Harness applies them locally. |
| `human` | `approval`, `quiz` | A person submits a terminal decision. |
| `codex_cli` | `direct_loop` | Runs one local Codex CLI turn with the API-frozen model, then reports normalized results and a commit proposal through `run_harness`. |

## Execution lifecycle

### 1. Create and persist an activity run

The API persists the activity snapshot, frozen Harness selection, run status,
checkpoint action, iteration, and continuation revision in SQLite.

For each `codex_cli` Activity, PipelineRun creation also freezes the effective
generator model as `requested_model` and resolves the generator Persona and its
ordered Skills from the User-owned instruction library. Their IDs, versions,
metadata, and content are persisted as a versioned `instruction_snapshot`
inside the immutable Activity snapshot. The `run_harness` checkpoint payload
returns that exact model and instruction snapshot; neither the API nor the
runtime resolves the mutable resources again. Codex authentication and the
executable remain local worker concerns; API Linked Services are not used.

### 2. Receive repository context from the runtime

The runtime sends repository snapshot context in `collect_snapshot`. The API uses
that context to build iteration prompts. For `codex_cli`, the runtime also
injects the frozen Persona instructions into the local turn prompt and exposes
each frozen Skill as `.agents/skills/<name>/SKILL.md` for that turn.

### 3. Build prompts

The execution generation service creates initial generator, retry generator, and
reviewer prompts. Prompt construction is centralized so orchestration code
never builds prompts directly.

### 4. Generator execution

The configured generator model receives the repository snapshot, user task, and
previous reviewer feedback on retries. The generator returns structured JSON
describing filesystem operations:

```json
{
  "operations": [
    {
      "operation": "replace",
      "path": "pages/index.vue",
      "content": "..."
    }
  ]
}
```

### 5. Validate and apply the operation contract

The API validates generator operations and returns them in checkpoint payload.
The runtime applies operations locally and reports success or failure in
`apply_operations`.

### 6. Receive review input

The runtime sends `final_diff` and changed file contents in
`submit_review_input`. The API uses this reviewer input as the decision source
of truth.

### 7. Reviewer execution

Each configured reviewer agent produces one independent review. Reviewers
receive the original task, Git diff, changed file contents, persona, and skill
instructions. Reviewers never receive the entire repository snapshot.

### 8. Aggregate review results

Every reviewer returns approval, feedback, and metrics. The aggregator approves
the iteration only if every reviewer approves. Otherwise, the feedback is
merged and returned to the generator.

### 9. Retry

If approval fails, repository context is rebuilt, reviewer feedback is appended,
and the generator runs again. The loop continues until every reviewer approves
or maximum iterations are reached.

### 10. Finalise

If the run succeeds, the API marks commit handoff as allowed. The runtime performs
the commit and reports the result. A commit-enabled Codex turn must propose a
non-empty `commit_message`; the API persists it and returns it in the later
`commit_if_allowed` payload. A `forbid` run neither requires the message nor
enters the commit checkpoint.
Every successful Codex result also contains `requested_model` and
`actual_model`. The API validates the requested value against the frozen
snapshot and persists both as runtime artifacts.

Successful and failed Codex results persist one normalized observation and
expose it as the ActivityRun `payload`. The observation includes start and end
timestamps, elapsed milliseconds, model and reasoning settings, session ID,
all numeric token counters, process exit code, diagnostics, materialized Skill
versions, source and final Git SHAs, diff, changed files, final response, and
failure detail. Partial JSONL observations survive a failed process. A later
successful `commit_if_allowed` replaces the pre-commit final SHA with the
authorized commit SHA.

## Prompt lifecycle

### Generator

Contains the repository snapshot and user task. Retry prompts additionally
include reviewer feedback.

### Reviewer

Contains the original task, Git diff, changed file contents, and review skill.

## Workspace and workflow ownership

Workspace lifecycle is runtime-owned. The API persists activity-run
orchestration state in SQLite.

The API queues a persisted Pipeline run. A Worker claims it, the frozen `louie`
Harness iterates the `/continue` checkpoint, commits an approved result, and
reports Activity outcomes so the API can select the next step.

Harnesses report normalized execution observations. A report can include a
final message, diff, changed files, duration, usage, bounded diagnostics, and
an optional opaque session reference. The API retains ownership of durable
state transitions, review decisions, retries, and commit authorization.

## Run artefacts

Every execution persists enough information for complete inspection. Typical
artefacts include:

- request;
- effective instruction snapshot;
- response;
- prompts;
- model responses;
- Git diffs;
- execution trace;
- metrics.

This makes every run reproducible and debuggable.

## Metrics

Metrics are collected for the generator, every reviewer, and the complete
execution. Current metrics include:

- input tokens;
- output tokens;
- cached tokens;
- reasoning tokens;
- duration;
- throughput.

Future versions will additionally expose execution cost and historical trends.
