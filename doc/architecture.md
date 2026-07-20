# Looping Louie Architecture

Looping Louie API is the decision engine for iterative LLM software
development.

Rather than trusting a single model to generate production-ready code, Looping
Louie orchestrates a structured workflow in which a generator proposes changes,
multiple specialised reviewers evaluate those changes, and the process repeats
until a configurable quality bar is reached.

The runtime is intentionally independent from any specific programming
language, framework or LLM provider.

---

## Repository Structure

Top-level packages and modules:

```text
app/

main.py
    HTTP API

routers/
    Endpoint composition

controllers/
    HTTP-level request orchestration

services/harness/
    Planning and reviewer decision helpers

services/model_context/
    Repository snapshot and prompt context construction

services/task_checkpoint/
    Checkpoint run path and operation contract parsing

services/llm_service/
    Provider-specific model integrations

services/execution_planner/
    Planner strategy for task execution

services/task_plan/
    Task list loading, selection and persistence

services/meeting/
    Multi-persona meeting orchestration

personas/
    Persona library and registry

skills/
    Skill library and registry

schemas/
    API contracts and shared models

models/
    Internal domain entities

utils/
    Shared IO and helper utilities
```

---

## High-Level Architecture

```text
                tasks.json
                     │
                     ▼
            Task Checkpoint Controller
                     │
                     ▼
        Planner + Generator
                     │
                     ▼
    Operation Contract (JSON operations)
                     │
                     ▼
           CLI Executes Locally
                     │
                     ▼
             Reviewer Skills
          │
          ▼
      Aggregator
          │
      Approved?
      │        │
      │No      │Yes
      ▼        ▼
 Retry      Commit allowed
             (CLI commits)
             Next task
```

---

## Execution Lifecycle

A single checkpoint task execution follows these steps.

### 1. Start run and persist API artefacts

Task execution artefacts (request, prompts, responses, operations,
review summaries, metrics) are persisted under the API runtime root:

```text
runtime/executions/<run_id>/
```

---

### 2. Receive repository context from CLI

CLI sends the repository snapshot context in `collect_snapshot`.

API uses that context to build iteration prompts.

---

### 3. Build prompts

The Prompt Builder creates:

- initial generator prompt
- retry generator prompts
- reviewer prompts

Prompt construction is centralised so orchestration code never builds prompts directly.

---

### 4. Generator execution

The configured generator model receives:

- repository snapshot
- user task
- previous reviewer feedback (on retries)

The generator returns structured JSON describing filesystem operations.

Example:

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

---

### 5. Validate operation contract and ask CLI to apply

API validates generator operations contract and returns them in checkpoint
payload.

CLI applies operations locally and reports success/failure in
`apply_operations`.

---

### 6. Receive diff and changed file contents from CLI

CLI sends `final_diff` and changed file contents in `submit_review_input`.

API uses this reviewer input as the decision source of truth.

---

### 7. Reviewer execution

Each configured skill becomes one independent reviewer.

Reviewers receive:

- original task
- git diff
- changed file contents
- skill definition

Reviewers never receive the entire repository snapshot.

---

### 8. Aggregate review results

Every reviewer returns:

- approved
- feedback
- metrics

The aggregator approves the iteration only if every reviewer approves.

Otherwise the feedback is merged and returned to the generator.

---

### 9. Retry

If approval fails:

- repository context is rebuilt
- reviewer feedback is appended
- generator runs again

The loop continues until:

- every reviewer approves
- maximum iterations are reached

---

### 10. Finalisation

If the run succeeds:

- API marks commit handoff as allowed.
- CLI performs the commit and reports the result.

---

## Prompt Lifecycle

Three prompt types currently exist.

### Generator

Contains:

- repository snapshot
- user task

Retry prompts additionally include reviewer feedback.

---

### Reviewer

Contains:

- original task
- git diff
- changed file contents
- review skill

---

### Skill Files

Skills are Markdown documents with YAML front matter.

Example:

```text
skills/

code_review/
    small_patch_quality.md

release/
    accessibility.md
```

---

## Workspace Lifecycle

Workspace lifecycle is CLI-owned.

API only persists orchestration artefacts under `runtime/executions/<run_id>/`.

---

## Task Lifecycle

Multi-task backlog orchestration is CLI-owned.

CLI workflow (conceptual):

```text
tasks.json

↓

first pending task

↓

call /task/start then iterate /task/continue

↓

approved?

↓

commit

↓

mark done

↓

next task
```

Execution stops immediately after the first rejected task.

---

## Skills

A skill is a reusable review policy.

Examples include:

- code quality
- Nuxt conventions
- UI preservation
- accessibility
- SEO
- security

Projects compose skills.

Skills remain project independent.

---

## Providers

Current providers:

- Together (generator)
- OpenAI (reviewers)

The architecture is intentionally provider independent.

Future providers may include:

- Anthropic
- Gemini
- local models
- enterprise models

The runner should not contain provider-specific logic.

---

## Run Artefacts

Every execution persists enough information for complete inspection.

Typical artefacts include:

- request
- response
- prompts
- model responses
- git diffs
- execution trace
- metrics

This makes every run reproducible and debuggable.

---

## Metrics

Metrics are collected for:

- generator
- every reviewer
- complete execution

Current metrics include:

- input tokens
- output tokens
- cached tokens
- reasoning tokens
- duration
- throughput

Future versions will additionally expose execution cost and historical trends.

---

## Design Principles

Looping Louie follows a small number of architectural principles.

- Git is the source of truth.
- Worktrees isolate every execution.
- Generators propose; reviewers validate.
- JSON file operations are preferred over LLM-generated patches.
- Git computes the real diff.
- One reviewer equals one responsibility.
- Prompt construction is centralised.
- Runs are fully observable.
- Tasks are committed independently.
- Small iterations are preferred over large rewrites.
- Simplicity is preferred over abstraction.
- The runtime owns the workflow; models are interchangeable.

---

## Current Limitations

The current MVP intentionally keeps the architecture simple.

Known limitations include:

- repository snapshots are static rather than task-aware;
- providers are not yet abstracted behind a common interface;
- reviewers operate on text only (no screenshots);
- file operations replace whole files rather than editing line ranges;
- execution is sequential;
- prompt caching is not yet implemented.

These limitations are tracked separately in `roadmap.md`.
