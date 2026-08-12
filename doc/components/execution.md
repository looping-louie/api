# Execution

A persisted loop run coordinates model decisions with CLI-owned repository
execution. The API plans and reviews changes; the CLI collects repository
context, applies operations, and performs the commit.

## Execution lifecycle

### 1. Create and persist a loop run

The API persists the loop snapshot, run status, checkpoint action, iteration,
and continuation revision in SQLite.

The run also persists a versioned `instructions-snapshot.json`. It contains the
instruction definitions available when the run starts. The same in-memory
snapshot is used for the entire run; execution services do not resolve those
definitions again.

### 2. Receive repository context from the CLI

The CLI sends repository snapshot context in `collect_snapshot`. The API uses
that context to build iteration prompts.

### 3. Build prompts

The loop-run generation service creates initial generator, retry generator, and
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
The CLI applies operations locally and reports success or failure in
`apply_operations`.

### 6. Receive review input

The CLI sends `final_diff` and changed file contents in
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

If the run succeeds, the API marks commit handoff as allowed. The CLI performs
the commit and reports the result.

## Prompt lifecycle

### Generator

Contains the repository snapshot and user task. Retry prompts additionally
include reviewer feedback.

### Reviewer

Contains the original task, Git diff, changed file contents, and review skill.

## Workspace and workflow ownership

Workspace lifecycle is CLI-owned. The API persists loop-run orchestration state
in SQLite.

The CLI creates a persisted run, iterates its `/continue` checkpoint, commits
an approved result, records workflow progress, and selects the next task.

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
